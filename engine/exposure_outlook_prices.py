"""Read-only research admission audit for Terminal's canonical intraday response.

The existing Terminal owns bars, identities, adjustments and market clocks. This
consumer decodes its documented display-epoch contract and exposes outstanding
research evidence, without adding a quote store or estimating missing bar values.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import re
from typing import Any

from engine.exposure_outlook_data import ET, _ROOT, _number, _timestamp


def terminal_bar_open_utc(epoch: int | float) -> datetime:
    """Decode the existing Terminal market-local display-epoch convention."""
    if (not isinstance(epoch, (int, float)) or isinstance(epoch, bool)
            or not 0 < epoch < 4_102_444_800 or epoch != int(epoch)):
        raise ValueError('invalid Terminal bar epoch')
    wall = datetime.fromtimestamp(epoch, timezone.utc)
    return wall.replace(tzinfo=ET).astimezone(timezone.utc)


def audit_terminal_intraday(payload: dict[str, Any], *, root: str, session: str,
                             as_of: str) -> dict[str, Any]:
    if not isinstance(root,str) or not _ROOT.fullmatch(root) or len(root)>12:
        raise ValueError('invalid option root')
    if not isinstance(session,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',session):
        raise ValueError('invalid session')
    day = date.fromisoformat(session)
    cutoff = _timestamp(as_of)
    if not isinstance(payload,dict):
        raise ValueError('expected Terminal intraday object')
    reasons: set[str] = {'INTRADAY_TRAINING_CORPUS_NOT_QUALIFIED'}
    out: dict[str,Any] = {
        'schema':'options.exposure_outlook.price_audit/v1', 'authority_tier':'research',
        'root':root, 'session':session, 'cutoff':cutoff.isoformat(), 'forecast_eligible':False,
        'bar_count':0, 'first_bar_open_utc':None, 'last_bar_close_utc':None,
        'point_in_time_availability':'not_verified', 'timestamp_basis':None,
    }
    def finish() -> dict[str,Any]:
        out['reason_codes'] = sorted(reasons)
        return out
    if payload.get('t') != root or payload.get('session_date') != session:
        reasons.add('IDENTITY_MISMATCH')
    tf = payload.get('tf')
    if tf not in ('1m','5m'):
        reasons.add('UNSUPPORTED_RESEARCH_TIMEFRAME')
        return finish()
    span = 60 if tf=='1m' else 300
    bars = payload.get('bars')
    if not isinstance(bars,list) or not bars:
        reasons.add('PRICE_BARS_UNAVAILABLE')
        return finish()
    out['bar_count'] = len(bars)
    if len(bars)>1440:
        reasons.add('PRICE_BAR_COUNT_LIMIT')
        return finish()
    for bar in bars:
        if (not isinstance(bar,list) or len(bar)!=6 or not all(_number(v) for v in bar)
                or bar[0] != int(bar[0]) or not 0 < bar[0] < 4_102_444_800
                or not 0 < bar[3] <= min(bar[1],bar[4]) <= max(bar[1],bar[4]) <= bar[2]
                or bar[5]<0):
            reasons.add('INVALID_PRICE_BARS')
            return finish()
    if any(b[0]-a[0] != span for a,b in zip(bars,bars[1:])):
        reasons.add('NON_CONTIGUOUS_PRICE_BARS')
    evidence = payload.get('source_evidence')
    if not isinstance(evidence,dict) or evidence.get('schema')!='terminal.intraday_source_evidence.v1':
        reasons.add('SOURCE_EVIDENCE_MISSING')
        return finish()
    if (evidence.get('symbol')!=root or evidence.get('requested_timeframe')!=tf
            or evidence.get('session')!='regular'):
        reasons.add('IDENTITY_MISMATCH')
    scope=evidence.get('response_scope')
    if not isinstance(scope,dict):
        scope={}
    if scope.get('requested_date')!=session:
        reasons.add('IDENTITY_MISMATCH')
    if scope.get('returned_bars')!=len(bars):
        reasons.add('SOURCE_EVIDENCE_COUNT_MISMATCH')
    if scope.get('first_bar_time')!=bars[0][0] or scope.get('last_bar_time')!=bars[-1][0]:
        reasons.add('SOURCE_EVIDENCE_RANGE_MISMATCH')
    counts=evidence.get('source_counts')
    if (not isinstance(counts,dict) or not counts
            or not all(isinstance(v,int) and not isinstance(v,bool) and v>=0 for v in counts.values())
            or sum(counts.values())!=len(bars)):
        reasons.add('SOURCE_EVIDENCE_COUNT_MISMATCH')
    for field in ('point_in_time_availability','instrument_identity','price_adjustment','completeness'):
        if evidence.get(field)!='verified':
            reasons.add(field.upper()+'_NOT_VERIFIED')
    out['point_in_time_availability']=evidence.get('point_in_time_availability','not_verified')
    basis=evidence.get('timestamp_basis')
    out['timestamp_basis']=basis
    # Only the currently published contract is supported. A future UTC contract
    # must be admitted explicitly, not guessed from the magnitude of an epoch.
    if basis!='market_local_display_epoch':
        reasons.add('UNSUPPORTED_TIMESTAMP_BASIS')
        return finish()
    opens=[]
    for bar in bars:
        actual=terminal_bar_open_utc(bar[0])
        if actual.astimezone(ET).date()!=day:
            reasons.add('BAR_SESSION_MISMATCH')
        opens.append(actual)
        if actual+timedelta(seconds=span)>cutoff:
            reasons.add('BAR_NOT_CLOSED_BY_CUTOFF')
    out['first_bar_open_utc']=opens[0].isoformat()
    out['last_bar_close_utc']=(opens[-1]+timedelta(seconds=span)).isoformat()
    out['calendar_completeness']='not_inferred_from_bar_count'
    return finish()
