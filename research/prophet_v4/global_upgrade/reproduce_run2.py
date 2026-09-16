"""Reproduce Run 2 in an explicitly chosen research directory, never a live data root.

Requires pandas and numpy. Example:
  python reproduce_run2.py --evidence-dir /path/to/isolated/prophet-research
Only missing immutable PUBLIC GitHub source is fetched. Existing differing bytes
are refused, never replaced. All writes remain under the supplied directory.
This characterizes known defects; it does not fix or promote a production model.
"""
from __future__ import annotations
import argparse
import ast
import copy
import datetime as dt
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import statistics
import sys
import types
import urllib.request
import numpy as np
import pandas as pd

PIN = 'c37c4e37b20ada935f32516a2a31428d558430c3'
BASE = f'https://raw.githubusercontent.com/mastermindx-market-intelligence/macro/{PIN}/'
BLOBS = {
 'site/factordata/us_track_ledger.json':'8936a655604eb2855b6a32d9820b8ca0b1eda095',
 'site/factordata/cn_track_ledger.json':'40ee54f0f4f464bb9c69aa24a516011e958c80b0',
 'site/factordata/hk_track_ledger.json':'f3829dd28cf28c969b9dd4bab4c549f34946a734',
 'site/factordata/ca_track_ledger.json':'dd7628f26fd1341e4752477ffd6c6c2b861408c4',
 'site/factordata/us_standouts.json':'f977d7619c3f1670fa0afb58b9deed9ce86680ed',
 'site/factordata/china_standouts.json':'0edba42f31af0539bed991f1b2c46e96ace7e5f4',
 'data/board_ledger/ca_board.parquet':'e3588aaa5f40fe7e6e8944fb640ba02789836b2f',
 'data/board_ledger/hk_board.parquet':'6b9ec8804ff601d100f939d743241f00f1ddc29f',
 'engine/us_prophet_fusion.py':'210e070103b36f10bbbf19981420a17bb9fdc4fc',
 'engine/china_intel_interest.py':'cb7e1895c75a560b09f8207de8aa58bc4389bafe',
 'engine/board_ledger.py':'004dc416819f2bc2b6887b2c3d7534410fd6fcb4',
 'engine/grading.py':'1208a7aa597159969a0ed7ccd359972bc413941a',
 'engine/track_scoring.py':'dfd046aa9244c9a22eee44bf05927075810d2b30',
 'engine/track_ledger.py':'a49bdfd40fc57dcc2e5e4732e1ec029c3a8c1199',
 'scripts/grade_us_board.py':'68ef9eb7620f0592e3cd02d66a3eae2ab0998dce',
}

def prepare(root: Path) -> Path:
    src = root / 'source'
    receipts = []
    for path, expected in BLOBS.items():
        dest = src / path
        if dest.exists():
            raw = dest.read_bytes()
        else:
            with urllib.request.urlopen(BASE + path, timeout=30) as response:
                raw = response.read(15_000_001)
            if len(raw) > 15_000_000:
                raise ValueError(f'Oversized source refused: {path}')
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        if blob != expected:
            raise ValueError(f'Immutable source mismatch, not overwritten: {path}')
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
        receipts.append(dict(path=path, git_blob=blob, sha256=hashlib.sha256(raw).hexdigest()))
    (root / 'reproduction_source_receipt.json').write_text(json.dumps(receipts, indent=2))
    return src

def load(src: Path, name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, src / path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

def descriptive(rows: list[dict], key: str) -> dict:
    rows = [r for r in rows if r.get('m') and r.get(key) is not None]
    vals = [float(r[key]) for r in rows]
    return dict(n=len(vals), origin_dates=len({r['d'] for r in rows}),
        names=len({r['t'] for r in rows}), wins=sum(v > 0 for v in vals),
        win_pct=round(100 * sum(v > 0 for v in vals) / len(vals), 2) if vals else None,
        mean_pct=round(statistics.mean(vals), 4) if vals else None,
        median_pct=statistics.median(vals) if vals else None)

def run(root: Path) -> dict:
    src = prepare(root)
    documents = {m:json.loads((src / f'site/factordata/{m}_track_ledger.json').read_text())
                 for m in ['us','cn','hk','ca']}
    out = dict(source_pin=PIN, source_hashes_verified=True,
               scope='Research characterization; not production acceptance, cost-adjusted backtest or alpha validation',
               versions=dict(python=sys.version, numpy=np.__version__, pandas=pd.__version__))
    out['market_records'] = {}
    for market, doc in documents.items():
        assert doc['meta'].get('truncated', 0) == 0
        key = 'p' if market == 'us' else 'x'
        definitions = {r.get('bd') or doc['meta'].get('board_definition') or 'UNSTAMPED' for r in doc['rows']}
        groups = {definition:descriptive([r for r in doc['rows']
            if (r.get('bd') or doc['meta'].get('board_definition') or 'UNSTAMPED') == definition], key)
            for definition in sorted(definitions)}
        out['market_records'][market] = dict(as_of=doc['as_of'], grain=doc['meta']['grain'],
            headline=doc['summary'], descriptive_metric=key, definitions=groups)
    v3 = [r for r in documents['us']['rows'] if r.get('bd')=='us_prophet_v3']
    out['us_v3_excess'] = descriptive(v3, 'x')
    out['us_v3_exit_anatomy'] = {reason:descriptive([r for r in v3 if r.get('xr')==reason], 'p')
                               for reason in ['horizon','target','stop']}
    assert out['market_records']['us']['definitions']['us_prophet_v3']['n'] == 240
    assert out['market_records']['us']['definitions']['us_prophet_v3']['wins'] == 83
    china = json.loads((src/'site/factordata/china_standouts.json').read_text())
    out['china_ordering'] = china['ranking']['ordering']
    out['china_input_coverage'] = china['ranking']['input_coverage']['intel_interest']
    cn = load(src, 'run2_cn', 'engine/china_intel_interest.py')
    us = load(src, 'run2_us', 'engine/us_prophet_fusion.py')
    grading = load(src, 'run2_grading', 'engine/grading.py')
    checks = []
    def check(name, actual, expected, kind='control'):
        checks.append(dict(name=name, actual=actual, expected=expected,
                           desired_contract_met=actual==expected, classification=kind))
    base = dict(off_high_pct=-10, rs_20d=0, ret_20d=8, rolling_over=False)
    alt = dict(side='accumulate', convergence=.8, conviction100=80)
    changes = {'base':{}, 'near_high':{'off_high_pct':-2}, 'far_below_high':{'off_high_pct':-20},
               'strong_rs':{'rs_20d':20}, 'weak_rs':{'rs_20d':-10}, 'rolling_over':{'rolling_over':True}}
    cases = {k:cn.interest_score(altdata_row=alt, traj={**base, **v}) for k,v in changes.items()}
    out['cn_controlled_price_priors'] = cases
    check('CN off-high reward', cases['far_below_high']['score'] > cases['near_high']['score'], True)
    check('CN RS discount', cases['strong_rs']['score'] < cases['weak_rs']['score'], True)
    check('CN rolling-over guard', cases['rolling_over']['score'] < cases['base']['score'], True)
    check('CN absent stays null', cn.interest_score()['score'], None)
    for name, value, age, expected in [('positive_recent',2.,1,True), ('negative_recent',-2.,1,False),
         ('positive_day_zero',2.,0,True), ('positive_old',2.,61,False), ('absent',None,None,False)]:
        check('SUE_'+name, us.extract_members(dict(sue_z=value,sue_fresh_days=age))['sue_fresh'],
              expected, 'contract_characterization')
    board = json.loads((src/'site/factordata/us_standouts.json').read_text())
    out['live_board_sue_exposure'] = [dict(ticker=r['ticker'], sue_z=r.get('sue_z'), age=r.get('sue_fresh_days'))
                                    for r in board['buy'] if r.get('sue_z') is not None]
    tree = ast.parse((src/'engine/board_ledger.py').read_text())
    node = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_is_suspended')
    ns = dict(pd=pd, SUSPENSION_SESSIONS=5)
    exec(compile(ast.Module(body=[node],type_ignores=[]),'exact_suspension','exec'),ns)
    dates = pd.bdate_range('2026-08-19','2026-09-25').difference(pd.DatetimeIndex(['2026-09-07']))
    price = pd.Series(range(100,100+len(dates)),index=dates,dtype=float)
    check('Recent healthy series not suspended',ns['_is_suspended'](price.iloc[:4],price.index[1]),False,'contract_characterization')
    check('Older healthy series not suspended',ns['_is_suspended'](price.iloc[:9],price.index[1]),False)
    early = grading.forward_metrics(price.loc[:'2026-09-15'],'2026-08-19',horizons=(5,10,21))
    mature = grading.forward_metrics(price.loc[:'2026-09-21'],'2026-08-19',horizons=(21,))
    check('CA H21 immature September15',early['fwd_ret_21'],None)
    check('CA H5 H10 can mature',all(early[f'fwd_ret_{h}'] is not None for h in [5,10]),True)
    check('CA H21 can mature September21',mature['fwd_ret_21'] is not None,True)
    out['ca_calendar_control'] = dict(signal='2026-08-19', fill=early['fill_date'],
        through='2026-09-15', forward_sessions=int(((dates>early['fill_date'])&(dates<='2026-09-15')).sum()),
        first_calendar_h21='2026-09-21', holiday='2026-09-07', caveat='Synthetic complete calendar; no delivery promise')
    pool = [dict(ticker='P'+str(i),alpha=float(i),off_high=-20.+5*i,signal={'tier_cascade':t})
            for i,t in enumerate(['T3','T1','T2'])]
    scores = us.fuse_board(pool).scores
    changed = copy.deepcopy(pool)
    for i,row in enumerate(changed):
        row.update(regime='severe_risk_off',sector=['Tech','Utilities','Energy'][i],sector_regime='bear',macro_risk=99)
    check('US pool nonconstant',len(set(scores))>1,True)
    check('US standalone macro/sector fields ignored',scores==us.fuse_board(changed).scores,True)
    out['checks'] = checks
    assert len(checks)==16 and sum(x['desired_contract_met'] for x in checks)==13
    assert all(x['desired_contract_met'] for x in checks if x['classification']=='control')
    out['regional_parquet_maturation'] = {}
    for m,definition in [('ca','ca_prophet_branch_b_v1'),('hk','hk_prophet_v2')]:
        frame = pd.read_parquet(src/f'data/board_ledger/{m}_board.parquet')
        cur = frame[frame['board_definition'].eq(definition)]
        out['regional_parquet_maturation'][m] = dict(rows=len(cur),
            mfe_nonnull={str(h):int(cur[f'fwd_mfe_{h}'].notna().sum()) for h in [5,10,21,63]},
            native_regime_nonnull=int(cur['own_market_regime'].notna().sum()))
    # Exact emitter; controlled non-ranking helper dependencies are explicit.
    engine = types.ModuleType('engine')
    sys.modules['engine'] = engine
    engine.track_scoring = load(src,'engine.track_scoring','engine/track_scoring.py')
    engine.track_ledger = load(src,'engine.track_ledger','engine/track_ledger.py')
    engine.track_era = types.SimpleNamespace(us_era_meta=lambda:{})
    tree = ast.parse((src/'scripts/grade_us_board.py').read_text())
    node = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='emit_ledger')
    ns = dict(pd=pd,dt=dt,math=math,LEDGER_HORIZON=10,LEDGER_HISTORY_FROM='2026-01-01',
              BENCH='SPY',_TROUGH_LB=90,_TROUGH_TOL=.97,_ob_mask=lambda s:None,
              _norm_definition=lambda v:v,continuity_block=lambda *args:{})
    exec(compile(ast.Module(body=[node],type_ignores=[]),'exact_emitter','exec'),ns)
    dates = pd.bdate_range('2026-08-17',periods=18)
    prices = pd.DataFrame({'TEST':range(100,118)},index=dates,dtype=float)
    bench = pd.DataFrame({'SPY':[100.]*len(dates)},index=dates)
    def b(date,rank,sector):
        return dict(as_of=date,rank_by='us_prophet_v3',rows=[dict(ticker='TEST',lane='buy',position=rank,sector=sector,align_tier='T1')])
    first = b('2026-08-17',1,'InitialSector')
    before = ns['emit_ledger']([first],prices,bench)['rows'][0]
    after = ns['emit_ledger']([first,b('2026-08-18',99,'LaterSector')],prices,bench)['rows'][0]
    assert before['d']==after['d'] and before['p']==after['p'] and before['bd']==after['bd']
    assert before['rk']==1 and after['rk']==99
    assert before['sec']=='InitialSector' and after['sec']=='LaterSector'
    out['rank_clock_probe'] = dict(before=before,after=after,
        controlled_helpers=['era metadata','oscillator exit','continuity','literal definition normalization'])
    out['result'] = 'Characterization reproduced: 16 checks, 13 desired conditions met, 3 contract failures; rank-clock mutation separately reproduced. No defects repaired.'
    return out

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-dir',required=True,type=Path)
    args = parser.parse_args()
    root = args.evidence_dir.expanduser().resolve()
    root.mkdir(parents=True,exist_ok=True)
    result = run(root)
    path = root/'run2_reproduce_results.json'
    path.write_text(json.dumps(result,indent=2))
    print(result['result'])
    print(path)
