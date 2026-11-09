"""Frozen, research-only ^TNX observed-session swing comparison; no collector.

Consumes one existing capture and the supplied-formula research reference.
No native Pine parity, historical first-known time, continuous overnight path,
trading signal registration, portfolio authority, or production use is claimed.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from research.rates_direction.uploaded_formula_probe import calculate, cross
from engine.validation import newey_west_tstat

FAMILY='ric_swing_proxy_v1'
COMBINATIONS=('M','P','R','MP','MR','PR','MPR')
MODELS=('unconditional','trend_vol')+COMBINATIONS
LABELS=('down','no_hit','up')
SOURCE_SHA='687b93d52beeb141dbfc3ea3eff787b67da7b36daa8effedc19568cbe544d070'
SPEC={'warmup_bars':80,'minimum_training_labels':40,'horizon_bars':12,
      'delay_bars':1,'recency_bars':3,'volatility_bars':24,'trend_bars':5,
      'barrier_floor_bp':5.,'bp_per_source_unit':100.,'shrinkage':12.,
      'minimum_active_episodes':50,'primary':'MPR','capture_at':'2026-09-24T12:51:03Z',
      'evidence_tier':'corrected_history_proxy_feasibility_not_pine_parity'}
FROZEN_PATHS=('research/rates_direction/swing_proxy_pilot.py',
              'research/rates_direction/uploaded_formula_probe.py',
              'research/rates_direction/SWING_PROXY_PILOT_V1.md',
              'tests/test_rates_swing_proxy_pilot.py','engine/validation.py')
FREEZE=ROOT/'research/rates_direction/swing_proxy_freeze_v1.json'


def _utc(value):
    t=pd.Timestamp(value)
    if t.tzinfo is None: raise ValueError('timezone-aware instant required')
    return t.tz_convert('UTC')


def parse_capture(payload, captured_at):
    """Return hourly rows, session-anchored bars and explicit exclusion counts.

    Missing/invalid expected observations remain on the grid. Session schedules
    come from this provider payload, not an inferred equity-market calendar.
    """
    cut=_utc(captured_at)
    if payload.get('chart',{}).get('error'): raise ValueError('provider error')
    results=payload.get('chart',{}).get('result')
    if not isinstance(results,list) or len(results)!=1: raise ValueError('one result required')
    x=results[0]; meta=x.get('meta',{})
    if meta.get('symbol')!='^TNX' or meta.get('dataGranularity') not in ('1h','60m'):
        raise ValueError('wrong source symbol or interval')
    timestamps=x.get('timestamp',[])
    if any(type(t) is not int for t in timestamps) or any(b<=a for a,b in zip(timestamps,timestamps[1:])):
        raise ValueError('strictly ordered unique integer timestamps required')
    q=x['indicators']['quote'][0]
    if any(len(q.get(k,[]))!=len(timestamps) for k in ('open','high','low','close')):
        raise ValueError('unaligned OHLC arrays')
    periods=meta.get('tradingPeriods',{}).get('regular',[])
    if not periods: raise ValueError('provider session metadata required')
    sessions=[]
    for group in periods:
        for entry in group:
            start=pd.Timestamp(entry['start'],unit='s',tz='UTC')
            end=pd.Timestamp(entry['end'],unit='s',tz='UTC')
            if not start<end or end-start>pd.Timedelta(days=1): raise ValueError('invalid session')
            sessions.append((start,end))
    if any(sessions[i][0]<sessions[i-1][1] for i in range(1,len(sessions))):
        raise ValueError('overlapping or unordered sessions')
    lookup={pd.Timestamp(t,unit='s',tz='UTC'):i for i,t in enumerate(timestamps)}
    expected=set(); hrs=[]; bs=[]; quality=Counter()
    for start,end in sessions:
        session_hours={}
        t=start
        while t<end:
            stop=min(t+pd.Timedelta(hours=1),end); expected.add(t)
            if stop>cut:
                quality['not_closed_hourly_rows']+=1; t=stop; continue
            i=lookup.get(t)
            vals={k:q[k][i] if i is not None else None for k in ('open','high','low','close')}
            finite=all(isinstance(v,(int,float)) and not isinstance(v,bool) and np.isfinite(v) for v in vals.values())
            valid=finite and vals['low']<=min(vals['open'],vals['close'])<=max(vals['open'],vals['close'])<=vals['high']
            if i is None: quality['missing_expected_hourly_rows']+=1
            elif not valid: quality['invalid_ohlc_rows']+=1
            vals={k:float(v) if valid else np.nan for k,v in vals.items()}
            hrs.append({'start':t,'end':stop,'valid':bool(valid),**vals})
            session_hours[t]=hrs[-1]; t=stop
        t=start
        while t<end:
            stop=min(t+pd.Timedelta(hours=2),end)
            if stop>cut:
                quality['not_closed_target_bars']+=1; t=stop; continue
            keys=tuple(pd.date_range(t,stop,freq='h',inclusive='left'))
            selected=[session_hours[k] for k in keys]
            valid=all(r['valid'] for r in selected)
            bs.append({'end':stop,'start':t,'duration_seconds':int((stop-t).total_seconds()),
                       'session':str(start.date()),'hour_ids':keys,'valid':valid,
                       'open':selected[0]['open'] if valid else np.nan,
                       'high':max(r['high'] for r in selected) if valid else np.nan,
                       'low':min(r['low'] for r in selected) if valid else np.nan,
                       'close':selected[-1]['close'] if valid else np.nan})
            t=stop
    quality['off_grid_rows']=sum(t not in expected for t in lookup)
    h=pd.DataFrame(hrs,columns=['start','end','valid','open','high','low','close']).set_index('start')
    b=pd.DataFrame(bs,columns=['end','start','duration_seconds','session','hour_ids','valid','open','high','low','close']).set_index('end')
    h.index=pd.DatetimeIndex(h.index,tz='UTC') if h.empty else pd.DatetimeIndex(h.index)
    b.index=pd.DatetimeIndex(b.index,tz='UTC') if b.empty else pd.DatetimeIndex(b.index)
    for key in ('missing_expected_hourly_rows','invalid_ohlc_rows','off_grid_rows','not_closed_hourly_rows','not_closed_target_bars'):
        quality.setdefault(key,0)
    quality.update(raw_rows=len(timestamps),closed_hourly_rows=len(h),closed_target_bars=len(b),
                   valid_target_bars=int(b.valid.sum()),session_count=len(sessions))
    return h,b,dict(quality)


def recent_state(up,down,alignment,recency):
    out=np.zeros(len(up),dtype=int); last=-recency; direction=0
    for i in range(len(up)):
        if bool(up.iloc[i]): last,direction=i,1
        elif bool(down.iloc[i]): last,direction=i,-1
        if i-last<recency and alignment.iloc[i]==direction: out[i]=direction
    return pd.Series(out,index=up.index)


def build_features(bars,spec=SPEC):
    """One-sided formulas; a missing expected bar resets indicator warmup."""
    out=pd.DataFrame(index=bars.index)
    for key in ('vol','trend','barrier_bp'): out[key]=np.nan
    for name in COMBINATIONS: out[name]=0
    out['eligible']=False
    valid=bars.valid.astype(bool).to_numpy(); i=0
    while i<len(bars):
        if not valid[i]: i+=1; continue
        end=i+1
        while end<len(bars) and valid[end]: end+=1
        seg=bars.iloc[i:end]; v=calculate(seg); f=pd.DataFrame(index=seg.index)
        for name,up,dn,alignment in (
            ('M',v.m_up,v.m_down,np.sign(v['hist'])),
            ('P',v.p_strict_up,v.p_strict_down,np.sign(v.kp-v.dp)),
            ('R',cross(v.kr,v.dr,'up'),cross(v.kr,v.dr,'down'),np.sign(v.kr-v.dr))):
            f[name]=recent_state(up,dn,alignment,spec['recency_bars'])
        for name in COMBINATIONS[3:]:
            selected=f[list(name)]
            f[name]=np.where((selected==1).all(axis=1),1,np.where((selected==-1).all(axis=1),-1,0))
        f['vol']=seg.close.diff().mul(spec['bp_per_source_unit']).rolling(spec['volatility_bars']).std()
        f['trend']=np.sign(seg.close.diff(spec['trend_bars']))
        f['barrier_bp']=np.maximum(spec['barrier_floor_bp'],f.vol*np.sqrt(spec['horizon_bars']))
        f['eligible']=(np.arange(len(seg))>=spec['warmup_bars']) & v[['m','sig','kp','dp','kr','dr']].notna().all(axis=1) & f.vol.notna()
        out.loc[seg.index,f.columns]=f
        i=end
    return out


def label_paths(hourly,bars,features,spec=SPEC):
    out=[]; n=len(bars)
    for i in range(n):
        entry=i+spec['delay_bars']; end=entry+spec['horizon_bars']
        row={'label':'censored','entry_reference':None,'target_end':None,'target_end_index':end,
             'barrier_bp':None,'up_excursion_bp':None,'down_excursion_bp':None}
        barrier=features.barrier_bp.iloc[i]
        if end>=n or not np.isfinite(barrier) or not bars.valid.iloc[i:end+1].all():
            out.append(row); continue
        reference=float(bars.close.iloc[entry]); delta=barrier/spec['bp_per_source_unit']
        ids=[k for group in bars.hour_ids.iloc[entry+1:end+1] for k in group]
        future=hourly.loc[ids]
        if not future.valid.all(): out.append(row); continue
        label='no_hit'
        for r in future.itertuples():
            up=r.high>=reference+delta; down=r.low<=reference-delta
            if up or down:
                label='ambiguous' if up and down else 'up' if up else 'down'; break
        row.update(label=label,entry_reference=reference,target_end=bars.index[end].isoformat(),
                   barrier_bp=float(barrier),
                   up_excursion_bp=float((future.high.max()-reference)*spec['bp_per_source_unit']),
                   down_excursion_bp=float((future.low.min()-reference)*spec['bp_per_source_unit']))
        out.append(row)
    return out


def _counts(labels,indices):
    return np.bincount([LABELS.index(labels[j]['label']) for j in indices],minlength=3).astype(float)


def walk_forward(bars,features,labels,spec=SPEC):
    rows=[]; usable=[i for i in range(len(bars)) if bool(features.eligible.iloc[i])]
    for i in usable:
        train=[j for j in usable if j<i and labels[j]['target_end_index']<i and labels[j]['label'] in LABELS]
        if len(train)<spec['minimum_training_labels']: continue
        uncond=(_counts(labels,train)+1)/(len(train)+3)
        median=float(np.median(features.vol.iloc[train]))
        same=[j for j in train if features.trend.iloc[j]==features.trend.iloc[i]
              and (features.vol.iloc[j]>median)==(features.vol.iloc[i]>median)]
        shrink=spec['shrinkage']; base=(_counts(labels,same)+shrink*uncond)/(len(same)+shrink)
        probs={'unconditional':uncond.tolist(),'trend_vol':base.tolist()}; states={}
        for name in COMBINATIONS:
            state=int(features[name].iloc[i]); states[name]=state
            matched=[j for j in same if int(features[name].iloc[j])==state]
            p=base if state==0 else (_counts(labels,matched)+shrink*base)/(len(matched)+shrink)
            probs[name]=p.tolist()
        rows.append({'origin_index':i,'origin':bars.index[i].isoformat(),'session':str(bars.session.iloc[i]),
                     'training_n':len(train),'last_training_target_end':max(labels[j]['target_end'] for j in train),
                     'probabilities':probs,'states':states,'outcome':labels[i],
                     'native_pine_parity':False,'historical_availability_qualified':False,'authority':False})
    return rows


def summarize(rows,spec=SPEC):
    """Compare common origins; episode selection cannot depend on outcomes."""
    scored=[r for r in rows if r['outcome']['label'] in LABELS]
    report={'forecast_origins':len(rows),'scored_origins':len(scored),
            'outcome_counts':dict(Counter(r['outcome']['label'] for r in rows)),
            'models':{},'primary':spec['primary'],'primary_promoted':False,
            'score_convention':'three-class sum Brier, range 0 to 2',
            'scope':spec['evidence_tier'],'equity_test_run':False,'authority':False}
    if not scored:
        report['status']='INSUFFICIENT_TRAINING_OR_OUTCOMES'; return report
    target=np.array([LABELS.index(r['outcome']['label']) for r in scored])
    truth=np.eye(3)[target]; losses={}
    for name in MODELS:
        probabilities=np.array([r['probabilities'][name] for r in scored])
        loss=((probabilities-truth)**2).sum(axis=1); losses[name]=loss
        item={'n':len(scored),'brier':float(loss.mean()),
              'log_loss':float(-np.log(probabilities[np.arange(len(target)),target]).mean()),
              'active_forecast_origins':0,'episodes':[]}
        if name in COMBINATIONS:
            item['active_forecast_origins']=sum(r['states'][name]!=0 for r in rows)
            last_end=-1
            for r in rows:
                state=r['states'][name]
                if state and r['origin_index']>last_end:
                    last_end=r['outcome']['target_end_index']
                    item['episodes'].append({'origin':r['origin'],'direction':state,
                                             'outcome':r['outcome']['label'],
                                             'barrier_bp':r['outcome']['barrier_bp'],
                                             'up_excursion_bp':r['outcome']['up_excursion_bp'],
                                             'down_excursion_bp':r['outcome']['down_excursion_bp']})
            eligible=[e for e in item['episodes'] if e['outcome'] in LABELS]
            wins=sum(e['outcome']==('up' if e['direction']>0 else 'down') for e in eligible)
            item.update(nonoverlapping_episodes=len(item['episodes']),resolved_episodes=len(eligible),
                        wins=wins,hit_fraction=wins/len(eligible) if eligible else None,
                        episode_counts=dict(Counter(e['outcome'] for e in item['episodes'])),
                        enough_for_ranking=len(eligible)>=spec['minimum_active_episodes'])
        report['models'][name]=item
    for name in COMBINATIONS:
        difference=losses['trend_vol']-losses[name]
        per_day=pd.Series(difference,index=[r['session'] for r in scored]).groupby(level=0).mean()
        hac=newey_west_tstat(per_day,lags=3)
        report['models'][name].update(brier_improvement_vs_trend_vol=float(difference.mean()),
                                      relative_brier_improvement=float(difference.mean()/losses['trend_vol'].mean()),
                                      date_count=len(per_day),diagnostic_hac=hac)
    report['status']='FEASIBILITY_ONLY_NO_PROMOTION'
    return report


def file_hash(path): return sha256(Path(path).read_bytes()).hexdigest()


def verify_freeze(root,receipt):
    if receipt.get('source_sha256')!=SOURCE_SHA or receipt.get('spec')!=SPEC:
        raise ValueError('frozen source/spec mismatch')
    if set(receipt.get('files',{}))!=set(FROZEN_PATHS): raise ValueError('incomplete freeze')
    for path,digest in receipt['files'].items():
        if file_hash(Path(root)/path)!=digest: raise ValueError('post-freeze change: '+path)


def freeze():
    receipt={'schema':'ric.swing_proxy.freeze.v1','operation':'rates-direction-20260924-sol-001',
             'frozen_at':datetime.now(timezone.utc).isoformat(),'primary_outcomes_opened':False,
             'source_sha256':SOURCE_SHA,'spec':SPEC,
             'files':{name:file_hash(ROOT/name) for name in FROZEN_PATHS},
             'ledger_before_sha256':file_hash(ROOT/'data/trial_ledger.jsonl')}
    with FREEZE.open('x') as f: json.dump(receipt,f,indent=2,allow_nan=False)
    print(json.dumps(receipt,indent=2))


def run(capture,output):
    from engine.trial_ledger import TrialLedger
    receipt=json.loads(FREEZE.read_text()); verify_freeze(ROOT,receipt)
    if file_hash(capture)!=SOURCE_SHA: raise ValueError('capture bytes changed')
    ledger_path=ROOT/'data/trial_ledger.jsonl'
    if file_hash(ledger_path)!=receipt['ledger_before_sha256']: raise ValueError('ledger changed since freeze; reconcile')
    led=TrialLedger(path=ledger_path,family=FAMILY)
    if led.literal_n(): raise ValueError('study already registered; reconcile original run, do not repeat')
    output=Path(output); output.mkdir(parents=True,exist_ok=False)
    configs=[{'model':m,'spec':SPEC,'source_sha256':SOURCE_SHA,'freeze_sha256':file_hash(FREEZE)} for m in MODELS]
    registered=led.log_grid(configs,info_cutoff=SPEC['capture_at'],source='predeclared_proxy_feasibility',
                            note='Seen 2026 sample; supplied-formula reference; native Pine parity false; no promotion')
    registration={'family':FAMILY,'registered':registered,'literal_n':led.literal_n(),
                  'ledger_before_sha256':receipt['ledger_before_sha256'],
                  'ledger_after_sha256':file_hash(ledger_path),'freeze_sha256':file_hash(FREEZE)}
    (output/'registration.json').write_text(json.dumps(registration,indent=2))
    if registered!=len(MODELS): raise ValueError('partial registration; reconcile')
    # First market feature/outcome evaluation is below the durable registration.
    hourly,bars,quality=parse_capture(json.loads(Path(capture).read_text()),SPEC['capture_at'])
    features=build_features(bars); labels=label_paths(hourly,bars,features)
    rows=walk_forward(bars,features,labels); summary=summarize(rows)
    predictions=output/'predictions.jsonl'
    with predictions.open('x') as f:
        for row in rows: f.write(json.dumps(row,allow_nan=False)+'\n')
    summary.update(registration=registration,quality=quality,spec=SPEC,
                   prediction_sha256=file_hash(predictions),source_sha256=SOURCE_SHA,
                   first_bar=bars.index[0].isoformat() if len(bars) else None,
                   last_bar=bars.index[-1].isoformat() if len(bars) else None,
                   scheduled_stub_bars=int((bars.duration_seconds<7200).sum()),
                   eligible_feature_origins=int(features.eligible.sum()),
                   all_feature_origin_labels=dict(Counter(labels[i]['label'] for i in range(len(labels)) if features.eligible.iloc[i])),
                   native_pine_parity=False,historical_availability_qualified=False)
    (output/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False))
    print(json.dumps({'status':summary['status'],'quality':quality,
                      'forecasts':len(rows),'scored':summary['scored_origins'],
                      'models':{k:{a:b for a,b in v.items() if a in ('brier','resolved_episodes','wins','enough_for_ranking')} for k,v in summary['models'].items()},
                      'output':str(output)},indent=2))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['freeze','run'])
    p.add_argument('--capture',type=Path)
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    if a.action=='freeze': freeze()
    else:
        if a.capture is None or a.output is None: p.error('run requires --capture and --output')
        run(a.capture,a.output)


if __name__=='__main__': main()
