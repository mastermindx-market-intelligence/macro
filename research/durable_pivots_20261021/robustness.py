#!/usr/bin/env python3
"""Frozen-finalist anchor and price-basis sensitivity. No rule selection."""
import argparse, itertools, json, sys
from pathlib import Path
import pandas as pd
import study as st

def fixed_high_rules():
    rules=[]
    catalog={r['rule_id']:r for r in st.catalog_rules(st.base_rules())}
    for side in st.SIDES:
        for a,b in itertools.product(('1W','2W'),repeat=2):
            for mode in ('deep_rising','cross'):
                rules.append(catalog[f'{side}|S{a}:curl|M{b}:{mode}|none'])
        for a in ('1W','2W'):
            rules.append(catalog[f'{side}|S{a}:curl|Mnone|none'])
    return rules

def register(out):
    lock=json.loads((out/'selection_lock.json').read_text())
    repo=Path(__file__).resolve().parents[2];sys.path.insert(0,str(repo))
    from engine.trial_ledger import TrialLedger
    ledger=TrialLedger(path=out/'trial_ledger.jsonl',family='durable_pivot_confluence_20261021')
    configs=[]
    for p in itertools.product(range(2),range(3),range(2)):
        for v in lock['selected']:
            configs.append({'analysis':'anchor','phase2':p[0],'phase3':p[1],'phasew':p[2],
                            'basis':'price','rule_id':v['rule']['rule_id']})
    for v in lock['selected']:
        configs.append({'analysis':'basis','phases':'000','basis':'total_return','rule_id':v['rule']['rule_id']})
    for r in fixed_high_rules():
        for tf,mode in itertools.product(('1D','2D','3D'),('both_rising','macd_cross')):
            configs.append({'analysis':'waiting','rule_id':r['rule_id'],'lower_tf':tf,'mode':mode,'wait_max':10})
        for tf,mode in itertools.product(('1D','2D','3D'),(*st.LF_MODES,'opposing_cross')):
            configs.append({'analysis':'standardized_conflict','rule_id':r['rule_id'],'lower_tf':tf,'mode':mode,
                            'age_bins':[5,10,21],'distance_bins':[1,2],'depth_bins':[6],'min_per_cell':5})
    ledger.log_grid(configs,info_cutoff=str(st.CUTOFF.date()),note='Fixed robustness protocol; before examining held-out outcome summaries')
    st.dump(out/'robustness_registration.json',{'literal_additional_configurations':len(configs),
            'effective_ledger_n':ledger.effective_n(),'selection_lock_sha256':st.digest(out/'selection_lock.json'),
            'protocol_sha256':st.digest(Path(__file__).parent/'ROBUSTNESS_PROTOCOL.md'),
            'created_at':pd.Timestamp.now(tz='UTC').isoformat()})
    print('REGISTERED',len(configs),flush=True)

def run(manifest,out,phase,basis):
    lock=json.loads((out/'selection_lock.json').read_text());rules=[v['rule'] for v in lock['selected']]
    phase=tuple(map(int,phase.split(',')));tag=''.join(map(str,phase))+'_'+basis
    dest=out/'robustness';dest.mkdir(exist_ok=True)
    if phase==(0,0,0) and basis=='price':
        e=pd.read_parquet(out/'base_events.parquet');p=pd.read_parquet(out/'reference_pivots.parquet')
    else:
        bases=list({v['base']:v for v in rules}.values())
        e,p,_,_=st.build_events(manifest,bases,phase,basis,quiet=True)
    rows=[]
    for r in rules:
        for pool in ('primary','crypto'):
            q=st.select_events(e,r,'test',pool)
            rows.append({'variant':tag,'phase2':phase[0],'phase3':phase[1],'phasew':phase[2],'basis':basis,
                         'rule_id':r['rule_id'],'side':r['side'],'pool':pool,
                         **st.summarize(q,p,r['side'],'test',pool)})
    pd.DataFrame(rows).to_csv(dest/(tag+'.csv'),index=False)
    print('SENSITIVITY_COMPLETE',tag,len(rows),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--phase',default='0,0,0');p.add_argument('--basis',default='price');p.add_argument('--register',action='store_true')
    a=p.parse_args()
    if a.register:register(a.out)
    else:run(a.manifest,a.out,a.phase,a.basis)
