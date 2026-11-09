"""Frozen R4 price-sequence experiment; no production policy or provider calls.

Protocol c458e016b094bbf28f6e4d89f5e622a56e92e697. Coinbase timestamps
are bar starts. Research conditions only become observable after bar completion.
"""
from __future__ import annotations

import copy
import hashlib
import json
import logging
import subprocess
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = Path(__file__).with_name('r4')
PLAN = 'c458e016b094bbf28f6e4d89f5e622a56e92e697'
BASE = '017d3866eace58c4587bd7d2dc07a9320450bd77'
OHLC = ['open', 'high', 'low', 'close']
HOUR = pd.Timedelta(hours=1)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def number(value):
    return float(value) if pd.notna(value) and np.isfinite(value) else None


def checked_grid(frame: pd.DataFrame, freq: str) -> tuple[pd.DataFrame, pd.Series]:
    if not isinstance(frame.index, pd.DatetimeIndex) or frame.index.tz is not None:
        raise ValueError('Require naive UTC DatetimeIndex')
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError('Require unique ordered source timestamps')
    if not frame.index.equals(frame.index.floor(freq)):
        raise ValueError('Require whole source bucket starts')
    if not set(OHLC).issubset(frame):
        raise ValueError('Missing OHLC')
    if frame.empty:
        return frame[OHLC].copy(), pd.Series(dtype=bool, index=frame.index)
    grid = frame[OHLC].apply(pd.to_numeric, errors='coerce').reindex(
        pd.date_range(frame.index[0], frame.index[-1], freq=freq))
    valid = (np.isfinite(grid).all(axis=1) & (grid > 0).all(axis=1)
             & (grid.high >= grid[['open','close','low']].max(axis=1))
             & (grid.low <= grid[['open','close','high']].min(axis=1)))
    return grid.where(valid, np.nan), valid


def hourly_conditions(frame: pd.DataFrame) -> pd.DataFrame:
    g, valid = checked_grid(frame, 'h')
    ret = g.close.pct_change(fill_method=None)
    sigma = ret.rolling(24).std(ddof=1).shift(1)
    known = valid.astype(int).rolling(74).sum().eq(74) & np.isfinite(sigma) & (sigma > 0)
    break_low = g.low.shift(1).rolling(72).min()
    d0 = (g.close < break_low).astype('boolean').where(known)
    d1 = (d0 & (ret <= -2*sigma)).astype('boolean').where(known)
    return pd.DataFrame({'d0': d0, 'd1': d1})


def daily_conditions(frame: pd.DataFrame) -> pd.DataFrame:
    g, valid = checked_grid(frame, 'D')
    known = valid.astype(int).rolling(6).sum().eq(6)
    washout = (g.close / g.close.shift(5) - 1 <= -.10).astype('boolean').where(known)
    reclaim = ((g.low >= g.low.shift(1)) & (g.low.shift(1) >= g.low.shift(2))
               & (g.close > g.high.shift(1)) & (g.close > g.close.rolling(5).mean()))
    return pd.DataFrame({'washout': washout, 'reclaim': reclaim.astype('boolean').where(known)})


def onsets(condition: pd.Series, *, step: str, separation: str) -> pd.DatetimeIndex:
    previous = condition.reindex(condition.index - pd.Timedelta(step))
    previous.index = condition.index
    fresh = condition.fillna(False) & previous.notna() & ~previous.fillna(True).astype(bool)
    selected = []
    for dt in condition.index[fresh]:
        if not selected or dt - selected[-1] > pd.Timedelta(separation):
            selected.append(dt)
    return pd.DatetimeIndex(selected)


def execution_time(start, *, bar_hours: int, delay_hours: int):
    return pd.Timestamp(start) + pd.Timedelta(hours=bar_hours + delay_hours)


def first_reclaim(daily: pd.DataFrame, anchor, max_days: int = 7):
    conditions = daily_conditions(daily).reclaim
    for n in range(1, max_days + 1):
        date = pd.Timestamp(anchor) + pd.Timedelta(days=n)
        value = conditions.get(date, pd.NA)
        if pd.isna(value):
            return 'unknown', None
        if bool(value):
            return 'confirmed', date
    return 'no_entry', None


def complete_window(hourly: pd.DataFrame, entry, hours: int):
    idx = pd.date_range(pd.Timestamp(entry), periods=hours+1, freq='h')
    window = hourly.reindex(idx)[OHLC]
    valid = (np.isfinite(window).all(axis=1) & (window > 0).all(axis=1)
             & (window.high >= window[['open','close','low']].max(axis=1))
             & (window.low <= window[['open','close','high']].min(axis=1)))
    # At the terminal timestamp only its opening trade belongs to this
    # experiment. Do not condition maturity on that later bar's high/low/close.
    valid.iloc[-1] = bool(np.isfinite(window.open.iloc[-1]) and window.open.iloc[-1] > 0)
    return window if valid.all() else None


def barrier_label(hourly: pd.DataFrame, entry, *, hours: int, lower: float, upper: float):
    if not (-1 < lower < 0 < upper) or hours < 1:
        raise ValueError('Invalid declared barriers/horizon')
    w = complete_window(hourly, entry, hours)
    if w is None:
        return {'category':'censored', 'barrier_hour':None, 'terminal_return':None,
                'worst_excursion':None, 'best_excursion':None}
    ref = float(w.open.iloc[0]); lo = ref*(1+lower); hi = ref*(1+upper)
    category, when = 'neither', None
    for i, (_, b) in enumerate(w.iloc[:-1].iterrows()):
        # Opening gaps establish order before an ambiguous high/low interval.
        if b.open <= lo:
            category = 'lower_first'
        elif b.open >= hi:
            category = 'upper_first'
        elif b.low <= lo and b.high >= hi:
            category = 'ambiguous'
        elif b.low <= lo:
            category = 'lower_first'
        elif b.high >= hi:
            category = 'upper_first'
        else:
            continue
        when = i
        break
    return {'category':category, 'barrier_hour':when,
            'terminal_return':float(w.open.iloc[-1]/ref-1),
            'worst_excursion':float(min(w.low.iloc[:-1].min(), w.open.iloc[-1])/ref-1),
            'best_excursion':float(max(w.high.iloc[:-1].max(), w.open.iloc[-1])/ref-1)}


def incumbent_targets(daily: pd.Series, index, *, delay_hours: int):
    available = pd.to_datetime(daily.index) + pd.Timedelta(days=1, hours=delay_hours)
    positions = available.searchsorted(index, side='right') - 1
    out = np.full(len(index), np.nan)
    valid = positions >= 0
    selected = np.maximum(positions, 0)
    age = pd.DatetimeIndex(index) - available.take(selected)
    valid &= age < pd.Timedelta(days=1)
    vals = pd.to_numeric(daily, errors='coerce').to_numpy()
    out[valid] = vals[selected[valid]]
    out[(out < 0) | (out > 1) | ~np.isfinite(out)] = np.nan
    return pd.Series(out, index=index)


def account_path(prices, targets, *, initial_weight=0., terminal_weight=0., cost_bps=10):
    """Event account, not a continuous strategy backtest or exact fill model.

    Drift holdings until requested targets change. A proportional turnover
    charge reduces pretrade wealth; targets are fractions of remaining wealth.
    The final target is an explicit liquidation/restoration trade.
    """
    p = np.asarray(prices, dtype=float); t = np.asarray(targets, dtype=float)
    if (len(p) < 2 or len(t) != len(p)-1 or not np.isfinite(p).all()
            or (p <= 0).any() or not np.isfinite(t).all() or (t < 0).any() or (t > 1).any()
            or not (0 <= initial_weight <= 1 and 0 <= terminal_weight <= 1 and 0 <= cost_bps < 10000)):
        raise ValueError('Unusable account path')
    wealth, weight, last_target, turnover = 1., float(initial_weight), float(initial_weight), 0.
    highwater, maxdd = 1., 0.
    cost = cost_bps / 10000.
    for k, target in enumerate(t):
        if target != last_target:
            change = abs(target-weight)
            wealth *= 1-cost*change
            turnover += change
            maxdd = min(maxdd, wealth/highwater-1)
            weight, last_target = float(target), float(target)
        ret = p[k+1]/p[k]-1
        gain = 1+weight*ret
        wealth *= gain
        weight = weight*(1+ret)/gain
        highwater = max(highwater, wealth)
        maxdd = min(maxdd, wealth/highwater-1)
    change = abs(terminal_weight-weight)
    wealth *= 1-cost*change
    turnover += change
    maxdd = min(maxdd, wealth/highwater-1)
    return {'wealth':float(wealth), 'return':float(wealth-1),
            'max_drawdown':float(maxdd), 'turnover':float(turnover)}


def interval90(frame: pd.DataFrame, field: str):
    """Frozen calendar-block resampling of event means; not a calibrated forecast."""
    f = frame.dropna(subset=[field])
    if f.empty:
        return None
    block = ((pd.to_datetime(f.anchor)-pd.Timestamp('2016-01-01'))/pd.Timedelta(days=90)).astype(int)
    groups = f.assign(block=block).groupby('block')[field].agg(['sum','count'])
    if len(groups) < 2:
        return None
    groups = groups.reindex(range(int(block.min()),int(block.max())+1), fill_value=0)
    rng = np.random.default_rng(20260928)
    draws = rng.integers(0,len(groups),size=(1000,len(groups)))
    n = groups['count'].to_numpy()[draws].sum(axis=1)
    value = groups['sum'].to_numpy()[draws].sum(axis=1)
    return [float(v) for v in np.quantile(value[n>0]/n[n>0], [.025,.975])]


def scoped(frame, period):
    start,end = period
    a = pd.to_datetime(frame.anchor)
    f = frame.loc[(a>=pd.Timestamp(start)) & (a<pd.Timestamp(end))].copy()
    # Keep the parent in the count but censor outcomes crossing the slice end.
    return f, pd.to_datetime(f.end) < pd.Timestamp(end)


def main():
    from engine import btc_inputs, btc_signals
    from lib import config, store
    OUT.mkdir(exist_ok=True)
    data = Path(config.data_dir())
    source_names = ['engine/btc_inputs.py','engine/btc_signals.py','engine/btc_overrides.py',
                    'engine/btc_decision.py','config.yml','lib/store.py',
                    'research/crypto_science/r4_sequence_study.py',
                    'research/CRYPTO_SCIENCE_R4_SEQUENCE_PREREG_2026-09-28.md']
    sources = {p:digest(ROOT/p) for p in source_names}
    old_evidence = {str(p.relative_to(ROOT)):digest(p) for parent in ['r2','r3']
                    for p in (Path(__file__).parent/parent).rglob('*')
                    if p.is_file() and '__pycache__' not in str(p)}
    gates = {str(p.relative_to(data)):digest(p) for p in (data/'vector').iterdir()
             if p.suffix in ['.json','.jsonl']}
    input_hashes, cached = {}, {}
    original_read, original_upsert = store.read, store.upsert
    def audited_read(group,name):
        safe = name.replace('^','_').replace('=','_').replace('/','_').replace(' ','_')
        path = data/group/(safe+'.parquet'); key = str(path.relative_to(data))
        if key not in cached:
            input_hashes[key] = digest(path) if path.exists() else None
            cached[key] = pd.read_parquet(path) if path.exists() else None
        value = cached[key]
        return None if value is None else value.copy(deep=True)
    def refuse_write(*args, **kwargs):
        raise RuntimeError('R4 research cannot mutate market stores')
    store.read, store.upsert = audited_read, refuse_write
    caught = []
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            logging.getLogger('engine.btc_inputs').setLevel(logging.ERROR)
            inputs = btc_inputs.load_all()
            corrected = btc_signals.compute_all(copy.deepcopy(inputs))
            hourly = audited_read('coinbase','btc_hourly')
            daily = audited_read('coinbase','btc_daily')
        print('Corrected incumbent recomputed; new price-only features use Coinbase only.', flush=True)
    finally:
        store.read, store.upsert = original_read, original_upsert
    # Immutable replay evidence only, not an issued forecast or second store.
    corrected[['alloc_optimal']].to_csv(OUT/'incumbent_replay_targets.csv', index_label='date')
    hc = hourly_conditions(hourly); dc = daily_conditions(daily)
    target_maps = {lag:incumbent_targets(corrected.alloc_optimal,hc.index,delay_hours=lag) for lag in [1,6]}
    h_selected = {k:onsets(hc[k], step='1h', separation='24h') for k in ['d0','d1']}
    washouts = onsets(dc.washout, step='1D', separation='14D')
    washouts = washouts[washouts>=pd.Timestamp('2016-01-01')]
    down, recovery, policies = [], [], []
    for key, dates in h_selected.items():
        for anchor in dates:
            for lag in [1,6]:
                entry = execution_time(anchor,bar_hours=1,delay_hours=lag)
                end = entry+pd.Timedelta(hours=24)
                row = {'family':'downside','rule':key,'anchor':str(anchor),'issue':str(anchor+HOUR),
                       'entry':str(entry),'end':str(end),'lag_hours':lag,
                       'prior24h_return':number(hourly.close.get(anchor,np.nan)/hourly.close.get(anchor-24*HOUR,np.nan)-1)}
                row.update(barrier_label(hourly,entry,hours=24,lower=-.05,upper=.03))
                down.append(row)
                w = complete_window(hourly,entry,24)
                target = target_maps[lag].reindex(pd.date_range(entry,end,freq='h'))
                row['policy_status'] = ('incomplete_price_window' if w is None else
                                        'incumbent_unavailable' if target.isna().any() else 'comparable')
                if w is None or target.isna().any():
                    continue
                for cost in [0,10,25]:
                    initial, terminal = float(target.iloc[0]), float(target.iloc[-1])
                    inc = account_path(w.open, target.iloc[:-1], initial_weight=initial,
                                       terminal_weight=terminal, cost_bps=cost)
                    cash = account_path(w.open, np.zeros(24), initial_weight=initial,
                                        terminal_weight=terminal, cost_bps=cost)
                    fixed = account_path(w.open, np.full(24,initial), initial_weight=initial,
                                         terminal_weight=initial, cost_bps=cost)
                    full = account_path(w.open,np.ones(24),initial_weight=1,terminal_weight=1,cost_bps=cost)
                    policies.append({'family':'downside','rule':key,'anchor':str(anchor),'entry':str(entry),
                        'end':str(end),'lag_hours':lag,'cost_bps':cost,'initial_exposure':initial,
                        'incumbent_return':inc['return'],'candidate_return':cash['return'],
                        'full_btc_return':full['return'],'fixed_initial_return':fixed['return'],
                        'candidate_minus_incumbent':cash['wealth']-inc['wealth'],
                        'incumbent_drawdown':inc['max_drawdown'],'candidate_drawdown':cash['max_drawdown'],
                        'candidate_turnover':cash['turnover']})
    print(f'Downside selected episodes: d0={len(h_selected["d0"])}, d1={len(h_selected["d1"])}',flush=True)
    for anchor in washouts:
        state, confirm = first_reclaim(daily,anchor)
        for lag in [1,6]:
            origin = execution_time(anchor,bar_hours=24,delay_hours=lag)
            end = origin+pd.Timedelta(hours=336)
            entry = execution_time(confirm,bar_hours=24,delay_hours=lag) if confirm is not None else None
            common = {'family':'recovery','anchor':str(anchor),'issue':str(anchor+pd.Timedelta(days=1)),
                      'end':str(end),'lag_hours':lag,'confirmation_state':state,
                      'confirmation_date':str(confirm) if confirm is not None else None}
            immediate = dict(common,rule='u0',entry=str(origin))
            immediate.update(barrier_label(hourly,origin,hours=168,lower=-.03,upper=.05))
            recovery.append(immediate)
            wait = dict(common,rule='u1',entry=str(entry) if entry is not None else None)
            wait.update(barrier_label(hourly,entry,hours=168,lower=-.03,upper=.05) if entry is not None
                        else {'category':'no_entry' if state=='no_entry' else 'censored',
                              'barrier_hour':None,'terminal_return':None,'worst_excursion':None,'best_excursion':None})
            recovery.append(wait)
            w = complete_window(hourly,origin,336)
            status = ('incomplete_common_price_window' if w is None else
                      'confirmation_unknown' if state=='unknown' else 'comparable')
            immediate['common_policy_status'] = wait['common_policy_status'] = status
            if w is None or state=='unknown':
                continue
            index = w.index
            target = target_maps[lag].reindex(index)
            immediate['incumbent_comparable'] = wait['incumbent_comparable'] = bool(target.notna().all())
            held = np.zeros(336) if entry is None else (index[:-1]>=entry).astype(float)
            fraction = float(held.mean())
            for cost in [0,10,25]:
                full = account_path(w.open,np.ones(336),cost_bps=cost)
                candidate = account_path(w.open,held,cost_bps=cost)
                matched = account_path(w.open,np.full(336,fraction),cost_bps=cost)
                inc = account_path(w.open,target.iloc[:-1],cost_bps=cost) if not target.isna().any() else None
                policies.append({'family':'recovery','rule':'u1','anchor':str(anchor),
                    'entry':str(origin),'candidate_entry':str(entry) if entry is not None else None,
                    'end':str(end),'lag_hours':lag,'cost_bps':cost,'confirmation_state':state,
                    'waiting_hours':float((entry-origin)/HOUR) if entry is not None else None,
                    'duration_matched_fraction_ex_post':fraction,
                    'immediate_return':full['return'],'candidate_return':candidate['return'],
                    'matched_duration_return_ex_post':matched['return'],'cash_return':0.,
                    'incumbent_return':inc['return'] if inc is not None else None,
                    'candidate_minus_immediate':candidate['wealth']-full['wealth'],
                    'candidate_minus_matched_ex_post':candidate['wealth']-matched['wealth'],
                    'candidate_minus_incumbent':candidate['wealth']-inc['wealth'] if inc is not None else None,
                    'immediate_drawdown':full['max_drawdown'],'candidate_drawdown':candidate['max_drawdown'],
                    'candidate_turnover':candidate['turnover']})
    frames = {'downside_events':pd.DataFrame(down),'recovery_events':pd.DataFrame(recovery),
              'policy_events':pd.DataFrame(policies)}
    for name, frame in frames.items():
        frame.to_csv(OUT/(name+'.csv'),index=False)
    periods = {'full':['2016-01-01','2027-01-01'],'2016_2019':['2016-01-01','2020-01-01'],
               '2020_2023':['2020-01-01','2024-01-01'],'reused_2024plus':['2024-01-01','2027-01-01']}
    event_summaries, policy_summaries = [], []
    for family in ['downside','recovery']:
        events = frames['downside_events' if family=='downside' else 'recovery_events']
        for period,bounds in periods.items():
            f, inside = scoped(events,bounds)
            f.loc[~inside,'category'] = 'censored'
            for (rule,lag), group in f.groupby(['rule','lag_hours']):
                mature = group.loc[~group.category.isin(['censored','no_entry'])].copy()
                success = 'lower_first' if family=='downside' else 'upper_first'
                mature['success'] = mature.category.eq(success).astype(float)
                event_summaries.append({'family':family,'period':period,'rule':rule,'lag_hours':int(lag),
                    'parents':len(group),'categories':{str(k):int(v) for k,v in group.category.value_counts().items()},
                    'mature_entries':len(mature),'successes':int(mature.success.sum()),
                    'hit_fraction':number(mature.success.mean()),'hit_block95':interval90(mature,'success'),
                    'median_prior24h_return':number(group.prior24h_return.median()) if 'prior24h_return' in group else None,
                    'median_worst_excursion':number(mature.worst_excursion.median()),
                    'median_terminal_return':number(mature.terminal_return.median())})
        pf = frames['policy_events'].loc[frames['policy_events'].family==family]
        for period,bounds in periods.items():
            f, inside = scoped(pf,bounds); f=f.loc[inside]
            for (rule,lag,cost), group in f.groupby(['rule','lag_hours','cost_bps']):
                fields = (['candidate_minus_incumbent','candidate_return','incumbent_return','fixed_initial_return']
                          if family=='downside' else ['candidate_minus_immediate','candidate_minus_matched_ex_post',
                                                    'candidate_minus_incumbent','candidate_return','immediate_return'])
                stats = {}
                for key in fields:
                    stats[key] = {'n':int(group[key].notna().sum()),'mean':number(group[key].mean()),
                                  'median':number(group[key].median()),'block95':interval90(group,key)}
                year = pd.to_datetime(group.anchor).dt.year
                diff = fields[0]
                excluded = {str(y):number(group.loc[year!=y,diff].mean()) for y in sorted(year.unique())}
                policy_summaries.append({'family':family,'period':period,'rule':rule,'lag_hours':int(lag),
                    'cost_bps':int(cost),'n_parents':len(group),'stats':stats,
                    'positive_entry_exposure':int((group.initial_exposure>0).sum()) if family=='downside' else None,
                    'confirmed':int(group.confirmation_state.eq('confirmed').sum()) if family=='recovery' else None,
                    'omit_one_year_primary_mean':excluded,
                    'per_year_counts':{str(k):int(v) for k,v in year.value_counts().sort_index().items()}})
    assert sources == {p:digest(ROOT/p) for p in sources}
    assert gates == {p:digest(data/p) for p in gates}
    assert all((digest(data/p) if (data/p).exists() else None)==h for p,h in input_hashes.items())
    assert old_evidence == {p:digest(ROOT/p) for p in old_evidence}
    result = {'classification':'FROZEN_RETROSPECTIVE_PRICE_SEQUENCE_EXPERIMENT_NOT_LIVE_POLICY',
        'plan_commit':PLAN,'baseline':BASE,
        'candidate_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'sources':sources,'input_hashes':input_hashes,'gate_hashes':gates,'prior_evidence_hashes':old_evidence,
        'hashes_unchanged':True,
        'coverage':{'hourly_rows':len(hourly),'hourly_first':str(hourly.index[0]),'hourly_last':str(hourly.index[-1]),
                    'daily_rows':len(daily),'hourly_known_counts':{k:int(hc[k].notna().sum()) for k in hc},
                    'washout_parents':len(washouts),'d0_episodes':len(h_selected['d0']),
                    'd1_episodes':len(h_selected['d1']),
                    'd0_d1_same_anchor_overlap':len(h_selected['d0'].intersection(h_selected['d1']))},
        'event_summaries':event_summaries,'policy_summaries':policy_summaries,
        'warnings':sorted(set(str(w.message) for w in caught)),
        'limitations':['Source-observed stored vintages, not historical publication attestation.',
                      'Costs and 1/6h delays are assumptions, not observed fills.',
                      'Paired event accounts are not independent trades or a compound strategy.',
                      'Duration-matched reference is ex-post, not tradable at washout.',
                      'No historical funding splice, real-flow feature, model fitting or live gate write.']}
    (OUT/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'coverage':result['coverage'],'event_rows':len(down)+len(recovery),
                      'policy_rows':len(policies),'summary_rows':len(event_summaries)+len(policy_summaries),
                      'hashes_unchanged':True},indent=2),flush=True)
    print('FROZEN_R4_STUDY_COMPLETE',flush=True)


if __name__=='__main__':
    main()
