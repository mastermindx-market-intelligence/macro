"""Chronological support of recorded-score metadata; computes no performance."""
from pathlib import Path
from datetime import date
import argparse, hashlib, importlib.util, json, sys
import numpy as np
import pandas as pd
sys.dont_write_bytecode = True
COLUMNS = ['as_of','lane','ticker','horizon','entry_date','snapshot_rank_by',
           'price_basis','recorded_horizon_d21','context_status']
INPUT_SHA256 = '366d94709ea8fef4ac91cc30cf4efd975b26e68a65766082e5ca8feb99aca6db'
CALENDAR_BLOB = '0ece6439ffe4b081ee7a268fe99b69e1de1216a3'

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def attach_bounds(frame, calendar):
    if any(c in frame for c in ('ret','excess_spy','excess_sector')):
        raise ValueError('This preflight accepts metadata, not outcome values')
    if not calendar.is_unique or not calendar.is_monotonic_increasing:
        raise ValueError('Calendar must be unique and sorted')
    out = frame.copy()
    out['as_of'] = pd.to_datetime(out.as_of)
    out['entry_date'] = pd.to_datetime(out.entry_date)
    positions = calendar.get_indexer(pd.DatetimeIndex(out.entry_date))
    h = pd.to_numeric(out.horizon,errors='raise').to_numpy(dtype=float)
    if not np.isfinite(h).all() or (h<1).any() or (h!=np.floor(h)).any():
        raise ValueError('Horizon must be a positive integer')
    ends = positions+h.astype(int)
    if (positions<0).any() or (ends>=len(calendar)).any():
        raise ValueError('Calendar cannot resolve an entry/endpoint bound')
    if out.as_of.isna().any() or not (out.entry_date>out.as_of).all():
        raise ValueError('Observation must precede a known entry')
    out['earliest_end'] = calendar[ends]
    return out

def window_support(frame):
    if frame.empty: raise ValueError('No observations in this stratum')
    prior_counts = []
    for observation in sorted(frame.as_of.unique()):
        prior = frame[(frame.as_of<observation)&(frame.earliest_end<observation)]
        prior_counts.append(int(prior.as_of.nunique()))
    overlap_start, overlap_end = frame.entry_date.max(),frame.earliest_end.min()
    return dict(rows=len(frame),signal_dates=int(frame.as_of.nunique()),
        first_signal=str(frame.as_of.min().date()),last_signal=str(frame.as_of.max().date()),
        first_entry=str(frame.entry_date.min().date()),last_entry=str(frame.entry_date.max().date()),
        earliest_calendar_completion=str(frame.earliest_end.min().date()),
        latest_calendar_completion=str(frame.earliest_end.max().date()),
        dates_with_optimistic_prior_training=sum(n>0 for n in prior_counts),
        max_optimistic_prior_training_dates=max(prior_counts),
        all_windows_share_calendar_interval=bool(overlap_start<=overlap_end),
        guaranteed_overlap_start=str(overlap_start.date()) if overlap_start<=overlap_end else None,
        guaranteed_overlap_end=str(overlap_end.date()) if overlap_start<=overlap_end else None)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-dir',type=Path,required=True)
    p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a = p.parse_args()
    if a.output.exists(): raise FileExistsError('Refusing to overwrite evidence')
    source = a.source_dir/'joined_grades.parquet'
    if digest(source)!=INPUT_SHA256: raise ValueError('Joined source changed')
    calendar_path = a.repo/'lib/nyse_calendar.py'
    raw = calendar_path.read_bytes()
    blob = hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    if blob!=CALENDAR_BLOB: raise ValueError('Calendar implementation changed')
    spec = importlib.util.spec_from_file_location('recorded_score_calendar',calendar_path)
    calendar_module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = calendar_module; spec.loader.exec_module(calendar_module)
    calendar = pd.DatetimeIndex(calendar_module.sessions_between(date(2026,1,1),date(2027,12,31)))
    meta = pd.read_parquet(source,columns=COLUMNS)
    target = meta[meta.lane.eq('buy')&meta.horizon.eq(21)&meta.context_status.eq('attached')].copy()
    if target.duplicated(['as_of','lane','ticker','horizon']).any():
        raise ValueError('Duplicate recorded observations')
    if not np.isfinite(pd.to_numeric(target.recorded_horizon_d21,errors='raise')).all():
        raise ValueError('Missing score support must be qualified separately')
    bounded = attach_bounds(target,calendar)
    rows = []
    for (ranker,basis),group in bounded.groupby(['snapshot_rank_by','price_basis'],dropna=False):
        rows.append(dict(ranker=ranker,price_basis=basis,**window_support(group)))
    result = pd.DataFrame(rows)
    a.output.mkdir(parents=True,exist_ok=False)
    result.to_csv(a.output/'temporal_support.csv',index=False)
    bounded.to_parquet(a.output/'metadata_with_calendar_bounds.parquet',index=False)
    result_receipt = dict(status='COMPLETE_METADATA_PREFLIGHT',authority='none',
        input_sha256=INPUT_SHA256,calendar_blob=CALENDAR_BLOB,columns_read=COLUMNS,
        outcome_values_read=False,performance_statistics_computed=False,
        target_rows=len(target),target_dates=int(target.as_of.nunique()),strata=len(result),
        strata_with_any_optimistic_temporal_training=int((result.dates_with_optimistic_prior_training>0).sum()),
        script_sha256=digest(__file__),source_unchanged=digest(source)==INPUT_SHA256,
        endpoint_semantics='Earliest exchange-session bound, not a regraded realized endpoint',
        inference='Zero eligible prior dates rules out within-stratum walk-forward training here; overlap is not an effective stock sample-size estimate',
        predictive_evaluation_admitted=False,
        pending=['canonical research accounting','independent review','historical publication timing','supported chronological/current-champion/regime coverage'])
    result_receipt['output_sha256'] = {f.name:digest(f) for f in a.output.iterdir() if f.is_file()}
    (a.output/'receipt.json').write_text(json.dumps(result_receipt,indent=2))
    print(json.dumps(result_receipt),flush=True)
    print(result.to_string(index=False),flush=True)

if __name__ == '__main__': main()
