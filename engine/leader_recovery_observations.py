"""Optional first-observed snapshots on the existing Leader Radar history rows.

Pure merge helper; NO independent path, writer, clock, event identity or scheduler.
Capture is opt-in. Disarming stops new captures but cannot erase earlier ones.
The hash checks consistency, not authenticity or first-seen market-data lineage.
"""
from __future__ import annotations
from datetime import date
import hashlib
import json
import pandas as pd

SCHEMA = 'leader_recovery_observation.v1'
COLUMNS = ('recovery_observed_at', 'recovery_observation_json', 'recovery_observation_sha256')


def _missing(value) -> bool:
    return value is None or (not isinstance(value, (str, dict, list)) and bool(pd.isna(value)))


def _key(row: dict) -> tuple[str, str]:
    ticker = row.get('ticker')
    stamp = pd.Timestamp(row.get('date'))
    if not isinstance(ticker, str) or not ticker or pd.isna(stamp) or stamp.tzinfo is not None or stamp != stamp.normalize():
        raise ValueError('ambiguous_history_identity')
    return stamp.date().isoformat(), ticker


def _validate_seal(row: dict) -> bool:
    values = [row.get(c) for c in COLUMNS]
    if all(_missing(v) for v in values):return False
    if any(_missing(v) for v in values):raise ValueError('partial_observation_seal')
    known_at, raw, digest = values
    if not all(isinstance(v,str) for v in values):raise ValueError('invalid_seal_type')
    if hashlib.sha256(raw.encode()).hexdigest() != digest:raise ValueError('observation_digest_mismatch')
    def unique(pairs):
        out={}
        for k,v in pairs:
            if k in out:raise ValueError('duplicate_json_key')
            out[k]=v
        return out
    payload=json.loads(raw,object_pairs_hook=unique,parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite_json')))
    stamp=pd.Timestamp(known_at)
    if stamp.tzinfo is None or pd.isna(stamp):raise ValueError('observation_requires_timezone')
    day,ticker=_key(row)
    if not isinstance(payload,dict) or payload.get('schema')!=SCHEMA or payload.get('ticker')!=ticker or payload.get('as_of')!=day or payload.get('observed_at')!=known_at:
        raise ValueError('observation_identity_clock_mismatch')
    if stamp.tz_convert('America/New_York').date().isoformat()<day:
        raise ValueError('observation_backdated_before_source')
    return True


def _capture(ticker: str, day: str, descriptor: dict, known_at: str) -> dict:
    if descriptor.get('schema')!='leader_recovery.v1' or descriptor.get('as_of')!=day:
        raise ValueError('descriptor_cut_mismatch')
    selected = {k:descriptor.get(k) for k in (
        'state','reason','prior_leader_on','entry_context','thesis_state',
        'definition_sha256','source_ref','source_fingerprint_sha256','sampling_basis',
        'evidence_mode','first_seen_qualified','historical_membership_qualified')}
    ep = descriptor.get('episode') or {}
    selected['episode'] = {k:ep.get(k) for k in (
        'opened_on','peak_on','peak_price','reference_rs','price_high_water',
        'max_drawdown_from_high_water','repair_floor','repair_started_on',
        'last_failure_on','failed_repairs','history_complete','recovered_on')}
    expectations=descriptor.get('expectations') or {}
    selected['expectations']={k:expectations.get(k) for k in (
        'source_date','source_fingerprint_sha256','availability','revision_direction','thesis_state')}
    payload={'schema':SCHEMA,'ticker':ticker,'as_of':day,'observed_at':known_at,
             'source_first_seen_proven':False,'descriptor':selected}
    raw=json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False)
    return dict(zip(COLUMNS,(known_at,raw,hashlib.sha256(raw.encode()).hexdigest())))


def merge_recovery_observations(previous: pd.DataFrame, updated: pd.DataFrame,
                                rows: list[dict], *, as_of: date,
                                observed_at: str, enabled: bool) -> pd.DataFrame:
    """Preserve earlier snapshots and optionally capture today's first descriptor.

    Called only by the incumbent nightly state_history writer. Reconstructive
    reruns can still change ordinary fields; captured observations remain exact.
    Both input frames and the input descriptors are non-mutated.
    """
    if type(enabled) is not bool:raise ValueError('enabled_must_be_boolean')
    has_existing=any(c in previous.columns for c in COLUMNS)
    if not enabled and not has_existing:return updated.copy(deep=True)
    old=previous.to_dict('records');new=updated.to_dict('records')
    retained={}
    for row in old:
        if _validate_seal(row):
            key=_key(row)
            if key in retained:raise ValueError('duplicate_sealed_history_identity')
            retained[key]=row
    keys=[_key(row) for row in new]
    if len(set(keys))!=len(keys):raise ValueError('duplicate_updated_history_identity')
    index={key:i for i,key in enumerate(keys)}
    # Restore snapshots lost by the native same-day remove-and-replace merge.
    for key,row in retained.items():
        if key not in index:
            index[key]=len(new);new.append(row.copy())
        for col in COLUMNS:new[index[key]][col]=row[col]
    if enabled:
        stamp=pd.Timestamp(observed_at)
        if pd.isna(stamp) or stamp.tzinfo is None:raise ValueError('observation_requires_timezone')
        cut=pd.Timestamp(as_of)
        if cut.tzinfo is not None or cut!=cut.normalize():raise ValueError('invalid_capture_date')
        day=cut.date().isoformat()
        if stamp.tz_convert('America/New_York').date().isoformat()<day:raise ValueError('observation_backdated_before_source')
        known_at=stamp.tz_convert('UTC').isoformat()
        seen=set()
        for row in rows:
            ticker=row['ticker']
            if ticker in seen:raise ValueError('duplicate_descriptor_identity')
            seen.add(ticker);key=(day,ticker)
            if key in retained:continue
            if key not in index:raise ValueError('descriptor_without_native_history_row')
            descriptor=(row.get('display_chips') or {}).get('leader_recovery') or {}
            if descriptor.get('schema')!='leader_recovery.v1':continue
            new[index[key]].update(_capture(ticker,day,descriptor,known_at))
    for row in new:_validate_seal(row)
    result=pd.DataFrame(new,columns=list(dict.fromkeys([*updated.columns,*previous.columns,*COLUMNS])))
    if 'date' in result:result['date']=pd.to_datetime(result['date'])
    for col in COLUMNS:result[col]=result[col].astype('string')
    return result


def read_captured_observation(history: pd.DataFrame, *, ticker: str,
                              source_session: date, known_at: str) -> dict:
    """Read only the exact first captured descriptor knowable by the requested time."""
    cut=pd.Timestamp(known_at)
    if pd.isna(cut) or cut.tzinfo is None:raise ValueError('knowledge_cut_requires_timezone')
    day=pd.Timestamp(source_session).date().isoformat()
    matches=[row for row in history.to_dict('records') if _key(row)==(day,ticker)]
    if len(matches)>1:raise ValueError('duplicate_history_identity')
    if not matches or not _validate_seal(matches[0]):
        return {'availability':'UNAVAILABLE','reason':'no_captured_observation','observation':None}
    row=matches[0]
    if pd.Timestamp(row[COLUMNS[0]])>cut:
        return {'availability':'UNAVAILABLE','reason':'not_known_at_requested_cut','observation':None}
    return {'availability':'CAPTURED_DESCRIPTOR','reason':None,
            'observation':json.loads(row[COLUMNS[1]]),
            'consistency_sha256':row[COLUMNS[2]],'source_first_seen_proven':False}
