"""Frozen R3 source-observed cohort diagnostic; no fitting, live gates or orders."""
from __future__ import annotations
import hashlib
import json
import subprocess
import sys
import types
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from engine import btc_inputs as inputs, btc_impulse_radar as radar, btc_impulse_radar_backtest as bt
from lib import config, store
BASELINE = '40ab75b261fba57b4357e1c7ffb38ddd62f62871'
PLAN = '953eedfa53a5a201efebc03b74853316cad6a2cf'
OUT = Path(__file__).resolve().parent / 'r3'


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def number(v):
    return float(v) if pd.notna(v) and np.isfinite(v) else None


def delayed_observations(fire, index, days):
    if days < 0:
        raise ValueError('No negative information lag')
    return fire.shift(freq=pd.Timedelta(days=days)).reindex(index).astype('boolean')


def episode_starts(fire, separation_days):
    """Observed false-to-true onsets; cooldown never sees outcome labels."""
    if separation_days < 0 or fire.index.has_duplicates or not fire.index.is_monotonic_increasing:
        raise ValueError('Invalid episode sequence')
    if fire.empty:
        return pd.DatetimeIndex([])
    calendar = pd.date_range(fire.index.min(), fire.index.max(), freq='D')
    daily = fire.reindex(calendar).astype('boolean')
    onset = (daily & daily.shift(1).eq(False)).fillna(False)
    selected = []
    for dt in daily.index[onset]:
        if not selected or (dt - selected[-1]).days > separation_days:
            selected.append(dt)
    return pd.DatetimeIndex(selected)


def block_hit_interval(events, hits):
    events, hits = np.asarray(events), np.asarray(hits)
    if len(events) != len(hits) or np.any(hits > events) or np.any(hits < 0):
        raise ValueError('Invalid event block counts')
    if np.count_nonzero(events) < 2:
        return None
    rng = np.random.default_rng(20260928)
    chosen = rng.integers(0, len(events), size=(1000, len(events)))
    n = events[chosen].sum(axis=1); h = hits[chosen].sum(axis=1)
    values = h[n > 0] / n[n > 0]
    return [float(x) for x in np.quantile(values, [0.025, 0.975])]


def summary(fire, label, period_mask, close, separation):
    eligible = fire.notna() & label.notna() & period_mask
    base, lift, n = bt._lift(fire, label, period_mask)
    fired = eligible & fire.fillna(False)
    hit_rows = int((label.fillna(False) & fired).sum())
    selected = episode_starts(fire, separation)
    selected = selected.intersection(close.index[period_mask])
    mature = selected.intersection(close.index[eligible])
    outcomes = label.loc[mature].astype(bool)
    false_n = int((~outcomes).sum())
    calendar = close.index[period_mask]
    if len(calendar):
        block_n = (calendar[-1] - calendar[0]).days // 30 + 1
        counts, hits = np.zeros(block_n, int), np.zeros(block_n, int)
        for dt, hit in outcomes.items():
            block = (dt - calendar[0]).days // 30
            counts[block] += 1; hits[block] += int(hit)
        interval = block_hit_interval(counts, hits)
    else:
        interval = None
    future = pd.concat([close.shift(-i) for i in range(1, bt.LABEL_H + 1)], axis=1)
    lo = future.min(axis=1, skipna=False) / close - 1
    hi = future.max(axis=1, skipna=False) / close - 1
    episodes = [{'date':str(dt.date()), 'hit':bool(hit),
                 'forward_min_pct':number(100*lo.loc[dt]), 'forward_max_pct':number(100*hi.loc[dt])}
                for dt, hit in outcomes.items()]
    return {'eligible_days':int(eligible.sum()), 'known_source_days':int((fire.notna() & period_mask).sum()),
        'positive_outcome_days':int(label.loc[eligible].sum()),
        'trigger_rows':n, 'hit_trigger_rows':hit_rows, 'base_rate':number(base),
        'conditional_event_frequency':hit_rows/n if n else None, 'lift':number(lift),
        'episode_separation_days':separation, 'selected_onsets':len(selected),
        'mature_episodes':len(mature), 'pending_or_ineligible_episodes':len(selected)-len(mature),
        'hit_episodes':int(outcomes.sum()), 'false_episodes':false_n,
        'episode_hit_fraction':float(outcomes.mean()) if len(outcomes) else None,
        'false_episodes_per_30_eligible_days':30*false_n/int(eligible.sum()) if eligible.any() else None,
        'episode_hit_fraction_block95':interval,
        'episode_forward_min_median_pct':number(lo.loc[mature].median()*100) if len(mature) else None,
        'episode_forward_max_median_pct':number(hi.loc[mature].median()*100) if len(mature) else None}, episodes


def main():
    OUT.mkdir(exist_ok=True)
    data = Path(config.data_dir())
    paths = [data/'vector/signals.parquet', data/'deribit/dvol.parquet',
             data/'bgeo/sopr.parquet', data/'bgeo/funding_rate.parquet']
    gate_paths = sorted(set((data/'vector').glob('*gate*.json')) | set((data/'vector').glob('*ledger*.json*')))
    source_paths = [ROOT/x for x in ['engine/btc_inputs.py','engine/btc_impulse_radar.py',
                   'engine/btc_impulse_radar_backtest.py','engine/btc_signals.py','config.yml','collectors/bgeo.py']]
    before = {str(p.relative_to(ROOT)):digest(p) for p in paths+gate_paths+source_paths}
    def reject(*args, **kwargs):
        raise RuntimeError('Research may not write market store or live gates')
    original_upsert, original_gate = store.upsert, bt.write_gate
    store.upsert, bt.write_gate = reject, reject
    try:
        sig = store.read('vector','signals'); close = sig['close']
        source = subprocess.check_output(['git','show',BASELINE+':engine/btc_impulse_radar.py'],cwd=ROOT,text=True)
        legacy = types.ModuleType('r2_original_radar')
        exec(compile(source,'<pinned-r2-radar>','exec'),legacy.__dict__)
        old = legacy.fire_series(sig)
        current_default = radar.fire_series(sig)
        pd.testing.assert_frame_equal(old,current_default)
        original_rate = inputs._col('bgeo','funding_rate')
        current_rate = inputs._funding()
        pd.testing.assert_series_equal(original_rate,current_rate)
        observed = radar.fire_series(sig,preserve_unknown=True)
        labels = dict(zip(('down','up'),bt._labels(close)))
        raw_rate = store.read('bgeo','funding_rate')
        overlap = raw_rate[['funding_rate_fundingRate','funding_rate']].dropna()
        funding = {'physical_column_order':list(raw_rate.columns),
          'current_rate_nonnull':int(current_rate.notna().sum()),
          'legacy_rate_nonnull':int(raw_rate['funding_rate'].notna().sum()),
          'overlap_rows':len(overlap),
          'overlap_exact_equal':bool(overlap.iloc[:,0].equals(overlap.iloc[:,1])) if len(overlap) else None,
          'current_values_unchanged':True,
          'old_new_semantic_equivalence':'NOT_ESTABLISHED',
          'annualization_interval':'8h assumption remains unqualified; no rescale/merge applied'}
        periods = {'full':pd.Series(True,index=sig.index),
                   'reused_2024_plus':pd.Series(sig.index>=pd.Timestamp('2024-01-01'),index=sig.index)}
        policies = {'R2_mature_only':current_default.astype('boolean'), 'observed_lag0':observed}
        for lag in (1,2):
            policies[f'observed_assumed_lag{lag}d'] = pd.DataFrame({k:delayed_observations(observed[k],sig.index,lag) for k in observed})
        rows, episode_rows = [], []
        for policy, frame in policies.items():
            for leg, spec in bt.LEGS.items():
                fire = frame[leg] if leg in frame else pd.Series(pd.NA,index=sig.index,dtype='boolean')
                for period, mask in periods.items():
                    for separation in (3,7):
                        metrics, episodes = summary(fire,labels[spec['dir']],mask,close,separation)
                        key = {'policy':policy,'leg':leg,'period':period,'direction':spec['dir']}
                        rows.append({**key,**metrics})
                        episode_rows.extend({**key,'separation_days':separation,**ep} for ep in episodes)
        # On observed dates, the qualified series must contain the identical boolean.
        parity = {}
        for leg in observed:
            valid = observed[leg].notna()
            if leg in current_default:
                assert (observed.loc[valid,leg].astype(bool).values==current_default.loc[valid,leg].values).all()
            parity[leg]={'observed_days':int(valid.sum()),'unknown_days':int((~valid).sum()),
                         'known_condition_parity':True}
        assert before == {str(p.relative_to(ROOT)):digest(p) for p in paths+gate_paths+source_paths}
        result = {'classification':'SOURCE_OBSERVED_RETROSPECTIVE_DIAGNOSTIC_NOT_PUBLICATION_QUALIFIED',
          'plan_commit':PLAN,'baseline':BASELINE,
          'candidate_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
          'script_sha256':digest(__file__),'input_source_gate_sha256':before,'unchanged':True,
          'runtime':{'python':sys.version,'pandas':pd.__version__,'numpy':np.__version__},
          'default_fire_parity':True,'funding':funding,'observations':parity,
          'outcome':'next3 daily closes +/-5%, matured; no achievable fill or account return claim',
          'limits':['No historical publication timestamps asserted','Delays are assumed, not measured',
                    'Episode separation avoids overlapping outcome windows, not all dependence',
                    'No new gate status or strategy promotion; 2024+ is reused',
                    'Bootstrap30calendar-day blocks, seed20260928,1000 draws; sparse intervals withheld'],
          'cohorts':rows}
        (OUT/'cohort_results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
        pd.DataFrame(episode_rows).to_csv(OUT/'episode_outcomes.csv',index=False)
        observed.to_csv(OUT/'source_observed_conditions.csv',index_label='date')
        print('R3_COMPLETE: defaults and current funding unchanged; all input/source/gate hashes stable')
        print(json.dumps({'funding':funding,'observations':parity,'cohort_rows':len(rows),'episode_rows':len(episode_rows)},indent=2))
        for r in rows:
            if r['period']=='reused_2024_plus' and r['episode_separation_days']==3:
                print(json.dumps({k:r[k] for k in ['policy','leg','eligible_days','trigger_rows','conditional_event_frequency','lift','mature_episodes','hit_episodes','episode_hit_fraction','false_episodes_per_30_eligible_days','episode_hit_fraction_block95']}))
    finally:
        store.upsert, bt.write_gate = original_upsert, original_gate

if __name__=='__main__':
    main()
