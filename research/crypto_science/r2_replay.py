"""Paired stored-vintage replay of R1 vs the R2 timing candidate.

No fitting, provider calls, store/gate writes or production publishing. This is
NOT historical availability certification or a new out-of-sample strategy test.
"""
from __future__ import annotations
import copy
import hashlib
import json
import logging
import subprocess
import sys
import types
import warnings
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from engine import btc_inputs, btc_signals, btc_impulse_radar_backtest as evaluator
from lib import config, store
BASE = "060c6bab567a7e45e6aad73393ade9aff9a55016"
OUT = Path(__file__).with_name("r2")
SOURCE_PATHS = ["engine/btc_signals.py", "engine/btc_impulse_radar_backtest.py",
                "engine/btc_inputs.py", "engine/btc_overrides.py", "engine/btc_impulse_radar.py",
                "engine/btc_decision.py", "config.yml", "lib/store.py", "lib/config.py"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git_source(path):
    return subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT, text=True)


def legacy_module(path, name):
    module = types.ModuleType(name)
    module.__file__ = str(ROOT / path)
    exec(compile(git_source(path), f"git:{BASE}:{path}", "exec"), module.__dict__)
    return module


def scalar(value):
    return float(value) if pd.notna(value) and np.isfinite(value) else None


def metric(close, allocation, start, cost_bps):
    """Declared close-to-close lagged exposure diagnostic, not fill modelling."""
    returns = close.pct_change(fill_method=None)
    held = allocation.shift(1)
    held.iloc[0] = 0.0
    changes = held.diff().abs()
    changes.iloc[0] = abs(held.iloc[0])
    daily = held * returns - changes * (cost_bps / 10000.0)
    daily.iloc[0] = 0.0
    daily = daily.loc[start:]
    if daily.empty or daily.isna().any() or not np.isfinite(daily).all() or (daily <= -1).any():
        return {"available": False, "reason": "invalid_or_incomplete_return_path"}
    equity = (1.0 + daily).cumprod()
    highwater = equity.cummax().clip(lower=1.0)
    years = max((daily.index[-1] - daily.index[0]).total_seconds() / (365.25 * 86400), 1/365.25)
    return {"available": True, "first": str(daily.index[0].date()), "last": str(daily.index[-1].date()),
            "n": len(daily), "one_way_cost_bps": cost_bps,
            "growth_annual_pct": scalar((equity.iloc[-1] ** (1/years) - 1) * 100),
            "max_drawdown_pct": scalar((equity / highwater - 1).min() * 100),
            "mean_exposure_pct": scalar(held.loc[start:].mean() * 100),
            "turnover_units": scalar(changes.loc[start:].sum()),
            "terminal_equity_multiple": scalar(equity.iloc[-1])}


def main():
    OUT.mkdir(exist_ok=True)
    data_root = Path(config.data_dir())
    source_before = {p: sha(ROOT/p) for p in SOURCE_PATHS}
    protected_paths = sorted((data_root/'vector').glob('*.json')) + sorted((data_root/'vector').glob('*.jsonl'))
    gates_before = {str(p.relative_to(data_root)): sha(p) for p in protected_paths}
    input_hashes, cached = {}, {}
    original_read, original_upsert = store.read, store.upsert

    def audited_read(group, name):
        safe = name.replace('^','_').replace('=','_').replace('/','_').replace(' ','_')
        path = data_root/group/(safe+'.parquet')
        key = str(path.relative_to(data_root))
        if key not in cached:
            if path.exists():
                input_hashes[key] = sha(path)
                frame = pd.read_parquet(path)
                frame.index = pd.to_datetime(frame.index)
                cached[key] = frame.sort_index()
            else:
                input_hashes[key] = None
                cached[key] = None
        frame = cached[key]
        return None if frame is None else frame.copy(deep=True)

    def refuse_write(*args, **kwargs):
        raise RuntimeError('No store writes are permitted in the research replay')

    store.read, store.upsert = audited_read, refuse_write
    caught = []
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            logging.getLogger('engine.btc_inputs').setLevel(logging.ERROR)
            logging.getLogger('engine.btc_impulse_radar').setLevel(logging.ERROR)
            inputs = btc_inputs.load_all()
            old = legacy_module('engine/btc_signals.py', 'btc_signals_r1_replay')
            old_eval = legacy_module('engine/btc_impulse_radar_backtest.py', 'btc_impulse_r1_replay')
            old_frame = old.compute_all(copy.deepcopy(inputs))
            new_frame = btc_signals.compute_all(copy.deepcopy(inputs))
            if not old_frame.index.equals(new_frame.index) or not old_frame.columns.equals(new_frame.columns):
                raise RuntimeError('Paired replay changed frame structure')
            print('Paired compute_all complete', len(new_frame), len(new_frame.columns), flush=True)
            changes = []
            for col in old_frame:
                a, b = old_frame[col], new_frame[col]
                availability = a.notna() != b.notna()
                if pd.api.types.is_numeric_dtype(a.dtype) and not pd.api.types.is_bool_dtype(a.dtype):
                    both = a.notna() & b.notna()
                    diff = (a[both] - b[both]).abs()
                    changed = int((diff > 1e-12).sum()) + int(availability.sum())
                    maximum = scalar(diff.max()) if len(diff) else None
                else:
                    same = a.eq(b).fillna(False) | (a.isna() & b.isna())
                    changed = int((~same).sum()); maximum = None
                if changed:
                    changes.append({'column': col, 'different_rows': changed,
                                    'availability_changed': int(availability.sum()), 'max_abs': maximum})
            unexpected = [r for r in changes if not (r['column']=='bottom_pressure' or r['column'].startswith('alloc_'))]
            if unexpected:
                raise RuntimeError(f'Unplanned paired changes: {unexpected}')
            # All available observation dates, including warm-up; compare final value of each prefix.
            px = inputs['price']
            old_bp, new_bp = old_frame['bottom_pressure'], new_frame['bottom_pressure']
            cutoffs = []
            for i, dt in enumerate(px.index):
                prefix = px.loc[:dt]
                old_last = old.bottom_pressure(prefix).iloc[-1]
                new_last = btc_signals.bottom_pressure(prefix).iloc[-1]
                cutoffs.append({'date': str(dt.date()), 'old_full': scalar(old_bp.loc[dt]),
                    'old_prefix': scalar(old_last), 'new_full': scalar(new_bp.loc[dt]),
                    'new_prefix': scalar(new_last), 'old_delta': scalar(old_bp.loc[dt]-old_last),
                    'new_delta': scalar(new_bp.loc[dt]-new_last), 'prefix_observations': i+1})
                if (i+1)%500==0:
                    print(f'Prefix checks {i+1}/{len(px)}', flush=True)
            rows = pd.DataFrame(cutoffs)
            rows.to_csv(OUT/'prefix_all_dates.csv', index=False)
            prefix_summary = {'tested': len(rows), 'warmup_under_200_rows': int((rows.prefix_observations<200).sum()),
                'old_changed': int((rows.old_delta.abs()>1e-12).sum()),
                'new_changed': int((rows.new_delta.abs()>1e-12).sum()),
                'old_max_abs': scalar(rows.old_delta.abs().max()), 'new_max_abs': scalar(rows.new_delta.abs().max())}
            if prefix_summary['new_changed']:
                raise RuntimeError(f'Candidate still repaints: {prefix_summary}')
            stats = []
            for label, frame in [('R1_original', old_frame), ('R2_corrected', new_frame)]:
                for col in frame:
                    if col.startswith('alloc_'):
                        for start in [frame.index[0], pd.Timestamp('2024-01-01')]:
                            for cost in [0.,10.,25.]:
                                stats.append({'candidate': label, 'variant':col, 'period':'full' if start==frame.index[0] else 'reused_2024_plus',
                                              **metric(frame['close'], frame[col], start, cost)})
            old_verdict = old_eval.validate(old_frame)
            new_verdict = evaluator.validate(old_frame)
            fires = evaluator.radar.fire_series(old_frame)
            label_counts = {}
            for name, ev in [('R1_original',old_eval), ('R2_corrected',evaluator)]:
                down, up = ev._labels(old_frame['close'])
                leg_rows = []
                for key,spec in ev.LEGS.items():
                    if key not in fires: continue
                    lab = down if spec['dir']=='down' else up
                    for period,mask in [('full',pd.Series(True,index=lab.index)),
                                        ('reused_2024_plus',pd.Series(lab.index>=pd.Timestamp(ev.HOLDOUT_START),index=lab.index))]:
                        m = lab.notna() & fires[key].notna() & mask
                        firing = m & fires[key]
                        leg_rows.append({'leg':key,'period':period,'mature_rows':int(m.sum()),
                            'events':int(lab[m].sum()),'fire_rows':int(firing.sum()),
                            'base_rate':scalar(lab[m].mean()),
                            'precision':scalar(lab[firing].mean()) if firing.any() else None})
                label_counts[name] = leg_rows
            stored = audited_read('vector','signals')
            stored_parity = []
            if stored is not None:
                common = old_frame.index.intersection(stored.index)
                for col in ['close','momentum','risk_index','bottom_pressure','alloc_optimal','alloc_optimal_raw']:
                    if col not in stored or col not in old_frame: continue
                    a,b = old_frame.loc[common,col],stored.loc[common,col]
                    both = a.notna() & b.notna()
                    d = (a[both]-b[both]).abs()
                    stored_parity.append({'column':col,'common_rows':len(common),
                        'different_rows':int((d>1e-9).sum()),'availability_changed':int((a.notna()!=b.notna()).sum()),
                        'max_abs':scalar(d.max())})
            latest = {'date':str(new_frame.index[-1].date()),'old_bottom_pressure':scalar(old_bp.iloc[-1]),
                      'new_bottom_pressure':scalar(new_bp.iloc[-1]),
                      'old_final_exposure_pct':scalar(old_frame.alloc_optimal.iloc[-1]*100),
                      'new_final_exposure_pct':scalar(new_frame.alloc_optimal.iloc[-1]*100)}
    finally:
        store.read, store.upsert = original_read, original_upsert
    for key,digest in input_hashes.items():
        path = data_root/key
        if (sha(path) if path.exists() else None) != digest:
            raise RuntimeError(f'Input changed during replay: {key}')
    if gates_before != {str(p.relative_to(data_root)):sha(p) for p in protected_paths}:
        raise RuntimeError('A protected data gate or ledger changed')
    if source_before != {p:sha(ROOT/p) for p in SOURCE_PATHS}:
        raise RuntimeError('Source changed during replay')
    warnings_summary = sorted({f'{type(w.message).__name__}: {w.message}' for w in caught})
    result = {'classification':'PAIRED_STORED_VINTAGE_DIAGNOSTIC_NOT_OUT_OF_SAMPLE',
        'baseline_ref':BASE,'candidate_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'source_sha256':source_before,'script_sha256':sha(__file__),
        'runtime':{'python':sys.version,'pandas':pd.__version__,'numpy':np.__version__},
        'input_sha256':input_hashes,'protected_gate_sha256':gates_before,'inputs_gates_source_unchanged':True,
        'frame_rows':len(new_frame),'frame_columns':len(new_frame.columns),
        'changed_columns':changes,'prefix_summary':prefix_summary,'latest':latest,
        'stored_baseline_parity':stored_parity,'diagnostic_metrics':stats,
        'old_impulse_verdict':old_verdict,'new_impulse_verdict':new_verdict,'label_counts':label_counts,
        'warnings':warnings_summary,
        'limits':['Current stored vintages, not as-published historical data.',
                  'Static current rules applied to history; no deployed decision reconstruction.',
                  'One-observation-lag close-return accounting; not an execution simulator.',
                  '0/10/25 bps assumptions are frozen cost sensitivity, not venue-qualified trading costs.',
                  '2024+ was reused earlier; not an untouched holdout.',
                  'Impulse fire rows overlap and existing feature-availability/selection limitations remain.',
                  'No live gate was written, no strategy fitted, no live position changed.']}
    (OUT/'paired_replay.json').write_text(json.dumps(result,ensure_ascii=False,allow_nan=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['frame_rows','frame_columns','changed_columns','prefix_summary','latest','stored_baseline_parity','old_impulse_verdict','new_impulse_verdict','inputs_gates_source_unchanged']},indent=2))


if __name__=='__main__':
    main()
