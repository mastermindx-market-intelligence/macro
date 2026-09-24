"""Expanded-capture replication adapter; reuse frozen pilot formulas and evaluator.

No model/threshold changes. Vectorized categorical counts are parity-tested
against the frozen implementation. Original pilot files and results stay intact.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from research.rates_direction import swing_proxy_pilot as p
from engine.trial_ledger import TrialLedger

SOURCE_SHA='1dc7e9121fd6aa36c5019beba303b629257eb1cab752ae937e4cef1aa8161b76'
SPEC={**p.SPEC,'capture_at':'2026-09-24T14:17:57Z'}
CUTOFF='2026-06-24T00:00:00Z'
PATHS=p.FROZEN_PATHS+('research/rates_direction/swing_proxy_extended.py',
                     'research/rates_direction/SWING_PROXY_EXTENDED_V1.md',
                     'tests/test_rates_swing_proxy_extended.py')
FREEZE=ROOT/'research/rates_direction/swing_proxy_extended_freeze_v1.json'


def fast_walk_forward(bars,features,labels,spec=SPEC):
    """Same probability math and purged clocks; arrays avoid repeated pandas indexing."""
    n=len(bars); eligible=features.eligible.to_numpy(bool)
    ids=np.arange(n); y=np.array([p.LABELS.index(r['label']) if r['label'] in p.LABELS else -1 for r in labels])
    ends=np.array([r['target_end_index'] for r in labels]); vol=features.vol.to_numpy(float)
    trend=features.trend.to_numpy(float); states={name:features[name].to_numpy(int) for name in p.COMBINATIONS}
    rows=[]; shrink=spec['shrinkage']
    def counts(mask): return np.bincount(y[mask],minlength=3).astype(float)
    for i in ids[eligible]:
        mask=eligible & (ids<i) & (ends<i) & (y>=0)
        train=ids[mask]
        if len(train)<spec['minimum_training_labels']: continue
        uncond=(counts(mask)+1)/(len(train)+3)
        median=float(np.median(vol[mask]))
        same=mask & (trend==trend[i]) & ((vol>median)==(vol[i]>median))
        base=(counts(same)+shrink*uncond)/(int(same.sum())+shrink)
        probabilities={'unconditional':uncond.tolist(),'trend_vol':base.tolist()}; now={}
        for name in p.COMBINATIONS:
            state=int(states[name][i]); now[name]=state
            matched=same & (states[name]==state)
            prob=base if state==0 else (counts(matched)+shrink*base)/(int(matched.sum())+shrink)
            probabilities[name]=prob.tolist()
        rows.append({'origin_index':int(i),'origin':bars.index[i].isoformat(),'session':str(bars.session.iloc[i]),
                     'training_n':len(train),'last_training_target_end':labels[int(train[-1])]['target_end'],
                     'probabilities':probabilities,'states':now,'outcome':labels[i],
                     'native_pine_parity':False,'historical_availability_qualified':False,'authority':False})
    return rows


def partition_rows(rows,bars,cutoff=CUTOFF):
    cut=p._utc(cutoff); out={'earlier':[],'overlap':[],'boundary':[]}
    for row in rows:
        if p._utc(row['origin'])>=cut: out['overlap'].append(row)
        elif row['outcome']['target_end_index']<len(bars) and bars.index[row['outcome']['target_end_index']]<cut:
            out['earlier'].append(row)
        else: out['boundary'].append(row)
    return out


def verify(receipt):
    if receipt.get('source_sha256')!=SOURCE_SHA or receipt.get('spec')!=SPEC or receipt.get('cutoff')!=CUTOFF:
        raise ValueError('frozen spec/source mismatch')
    if set(receipt.get('files',{}))!=set(PATHS): raise ValueError('incomplete freeze')
    for name,digest in receipt['files'].items():
        if p.file_hash(ROOT/name)!=digest: raise ValueError('post-freeze source change: '+name)


def freeze():
    # The original experiment's numerical/text/test bytes must remain unchanged.
    p.verify_freeze(ROOT,json.loads(p.FREEZE.read_text()))
    receipt={'schema':'ric.swing_proxy.extended_freeze.v1','frozen_at':datetime.now(timezone.utc).isoformat(),
             'strategy_outcomes_opened':False,'source_sha256':SOURCE_SHA,'spec':SPEC,'cutoff':CUTOFF,
             'files':{name:p.file_hash(ROOT/name) for name in PATHS},
             'ledger_before_sha256':p.file_hash(ROOT/'data/trial_ledger.jsonl'),
             'prior_family_trials':9,'new_configs':9,'primary':'earlier:MPR_vs_trend_vol',
             'native_pine_parity':False,'authority':False}
    with FREEZE.open('x') as f: json.dump(receipt,f,indent=2)
    print(json.dumps(receipt,indent=2))


def run(capture,output):
    receipt=json.loads(FREEZE.read_text()); verify(receipt)
    if p.file_hash(capture)!=SOURCE_SHA: raise ValueError('changed capture')
    ledger_path=ROOT/'data/trial_ledger.jsonl'
    if p.file_hash(ledger_path)!=receipt['ledger_before_sha256']: raise ValueError('changed ledger; reconcile')
    led=TrialLedger(path=ledger_path,family=p.FAMILY)
    if led.literal_n()!=9: raise ValueError('family state changed; reconcile')
    out=Path(output); out.mkdir(parents=True,exist_ok=False)
    configs=[{'model':name,'spec':SPEC,'source_sha256':SOURCE_SHA,'freeze_sha256':p.file_hash(FREEZE),
              'sample':'extended_capture','primary_partition_end_exclusive':CUTOFF} for name in p.MODELS]
    registered=led.log_grid(configs,info_cutoff=SPEC['capture_at'],source='unchanged_rule_extended_replication',
                            note='Same family9 prior+9 new; earlier dates primary, seen overlap separate; no PIT or promotion')
    registration={'family':p.FAMILY,'new_configs':registered,'literal_n':led.literal_n(),
                  'ledger_before_sha256':receipt['ledger_before_sha256'],'ledger_after_sha256':p.file_hash(ledger_path),
                  'freeze_sha256':p.file_hash(FREEZE)}
    (out/'registration.json').write_text(json.dumps(registration,indent=2))
    if registered!=9 or led.literal_n()!=18: raise ValueError('partial registration; reconcile')
    hourly,bars,quality=p.parse_capture(json.loads(Path(capture).read_text()),SPEC['capture_at'])
    features=p.build_features(bars,SPEC); labels=p.label_paths(hourly,bars,features,SPEC)
    rows=fast_walk_forward(bars,features,labels,SPEC); parts=partition_rows(rows,bars)
    with (out/'predictions.jsonl').open('x') as f:
        for row in rows: f.write(json.dumps(row,allow_nan=False)+'\n')
    summary={'schema':'ric.swing_proxy.extended_result.v1','spec':SPEC,'quality':quality,
             'registration':registration,'source_sha256':SOURCE_SHA,'cutoff':CUTOFF,
             'prediction_sha256':p.file_hash(out/'predictions.jsonl'),
             'forecasts':len(rows),'eligible_feature_origins':int(features.eligible.sum()),
             'primary_partition':'earlier','primary_candidate':'MPR','boundary_origins':len(parts['boundary']),
             'partitions':{name:p.summarize(group,SPEC) for name,group in parts.items() if name!='boundary'},
             'all_dates_diagnostic':p.summarize(rows,SPEC),'native_pine_parity':False,
             'historical_availability_qualified':False,'authority':False}
    (out/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False))
    print(json.dumps({'quality':quality,'forecasts':len(rows),'primary_scored':summary['partitions']['earlier']['scored_origins'],
                      'models':{k:{a:b for a,b in v.items() if a in ('brier','resolved_episodes','wins','relative_brier_improvement','enough_for_ranking')} for k,v in summary['partitions']['earlier']['models'].items()},
                      'output':str(out)},indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['freeze','run']); parser.add_argument('--capture',type=Path); parser.add_argument('--output',type=Path)
    a=parser.parse_args()
    if a.action=='freeze': freeze()
    else:
        if a.capture is None or a.output is None: parser.error('run requires capture and output')
        run(a.capture,a.output)


if __name__=='__main__': main()
