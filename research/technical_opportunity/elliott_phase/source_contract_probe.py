"""Read-only synthetic probe of an exact existing Macro source version.

No market prices, no writes, no model fitting, no production imports.
Default: obtain the pinned source with git show from an existing Macro checkout.
--source: use an explicitly provided source/AST-equivalent historical excerpt.
A successful probe documents behavior; it is NOT production or trading acceptance.
"""
from __future__ import annotations
import argparse
import ast
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import types

import pandas as pd

COMMIT = '4b1f8fddcc4eb6f36133fca4d42018678b74d30b'
SOURCE_PATH = 'engine/cycle_ontology.py'
BLOB = '9e726868f6c218a84cd50a9f976c77c3a347ac6c'
ASTS = {
    'TurnParams': 'c762a300057b5233fd15f35cabbdb840959feb19f65b0fed680845555a41a8b9',
    '_yf': 'e3537cb8d826f0fca5962f4b8b08e8d81d24b13d87169f906bb286236f88e105',
    'detect_turns': 'cb4d7b49ca3e2a2ef4c693bbe2c17e5e43f1539927eca3815520013d18f0147b',
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path,
                        help='Explicit source or AST-equivalent excerpt; otherwise use pinned git object')
    args = parser.parse_args()
    if args.source:
        raw = args.source.read_bytes()
        source_mode = 'explicit_source_or_excerpt'
    else:
        raw = subprocess.check_output(['git','show',f'{COMMIT}:{SOURCE_PATH}'],timeout=30)
        source_mode = 'pinned_git_object'
    blob = hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    if source_mode == 'pinned_git_object' and blob != BLOB:
        raise ValueError(f'Pinned blob mismatch: {blob}')
    tree = ast.parse(raw.decode('utf-8'))
    selected = [n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in ASTS]
    if {n.name for n in selected} != set(ASTS):
        raise ValueError('Required source definitions missing')
    for node in selected:
        digest=hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest()
        if digest != ASTS[node.name]:
            raise ValueError(f'AST mismatch for {node.name}: {digest}')
    module = types.ModuleType('_elliott_pinned_source_probe')
    sys.modules[module.__name__] = module
    module.__dict__.update(pd=pd,hashlib=hashlib,dataclass=dataclass,DETECTOR_VERSION=2)
    exec(compile(ast.Module(body=selected,type_ignores=[]),str(args.source or SOURCE_PATH),'exec'),module.__dict__)

    def run(values, dates=None, pct=14.0):
        dates = dates if dates is not None else pd.date_range('2020-01-01',periods=len(values))
        return module.detect_turns(pd.Series(values,index=dates,dtype=float),
            series_id='SYNTHETIC',params=module.TurnParams(pct=pct,basis='close_price'))

    daily=[r for r in run([100,120]*15) if not r['provisional']]
    intraday_dates=pd.date_range('2020-01-02 09:30',periods=30,freq='5min',tz='America/New_York')
    intra=[r for r in run([100,120]*15,intraday_dates) if not r['provisional']]
    lag=[r for r in run([100.0]*30+[120.0,float('nan'),float('nan'),100.0,100.0,100.0])
         if not r['provisional'] and r['k']=='peak'][0]
    result={
        'status':'synthetic_characterization_not_forecast_or_production_acceptance',
        'source_commit':COMMIT,
        'expected_source_blob':BLOB,
        'input_mode':source_mode,
        'input_matches_full_blob':blob==BLOB,
        'three_function_asts_verified':True,
        'confirmed_rows':len(daily),
        'distinct_turn_ids':len({r['turn_id'] for r in daily}),
        'hypothetical_id_keyed_rows':len({r['turn_id']:r for r in daily}),
        'intraday_confirmation_dates':sorted({r['confirmed_at'] for r in intra}),
        'intraday_lags':sorted({r['confirm_lag_bars'] for r in intra}),
        'warmup_29_has_output':bool(run([100,120]*14+[100])),
        'first_30_bar_output_earliest_confirmation':min(r['confirmed_at'] for r in daily),
        'first_output_fixture_date':'2020-01-30',
        'open_extreme_is_provisional':run(list(range(100,140)))[-1]['provisional'],
        'missing_slot_lag':lag['confirm_lag_bars'],
        'missing_slot_calendar_days':(pd.Timestamp(lag['confirmed_at'])-pd.Timestamp(lag['date'])).days,
        'limits':['No current production-consumer loss measured','No full Elliott grammar validated',
                  'Existing detector left unchanged','No market data or outcomes used'],
    }
    assert result['confirmed_rows']==29 and result['distinct_turn_ids']==2
    assert result['intraday_confirmation_dates']==['2020-01-02']
    assert result['intraday_lags']==[1]
    assert result['warmup_29_has_output'] is False
    assert result['first_30_bar_output_earliest_confirmation']=='2020-01-02'
    assert result['open_extreme_is_provisional'] is True
    assert (result['missing_slot_lag'],result['missing_slot_calendar_days'])==(1,3)
    print(json.dumps(result,indent=2))

if __name__ == '__main__':
    main()
