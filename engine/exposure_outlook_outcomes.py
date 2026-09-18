"""Observed outcomes over canonical Terminal bars; never a forecasting model.

Session windows and frozen bands are explicit caller inputs, not a second
calendar or target-selection authority. Missing path data cannot prove that a
barrier was never touched. OHLC bars cannot order two touches inside one bar.
This module does not write, train, publish forecasts, or grant research admission.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any

from engine.exposure_outlook_data import ET, _number, _timestamp
from engine.exposure_outlook_prices import audit_terminal_intraday, terminal_bar_open_utc

_HORIZONS = (30, 60, 90, 120, 'close')
_FATAL = frozenset({
    'IDENTITY_MISMATCH', 'INVALID_PRICE_BARS', 'PRICE_BARS_UNAVAILABLE',
    'PRICE_BAR_COUNT_LIMIT', 'SOURCE_EVIDENCE_MISSING', 'UNSUPPORTED_TIMESTAMP_BASIS',
    'SOURCE_EVIDENCE_COUNT_MISMATCH', 'SOURCE_EVIDENCE_RANGE_MISMATCH',
    'UNSUPPORTED_RESEARCH_TIMEFRAME', 'BAR_SESSION_MISMATCH',
})


def _digest(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(body.encode()).hexdigest()


def label_price_outcomes(payload: dict[str, Any], *, root: str, session: str,
                         origin: str, as_of: str, session_open: str,
                         session_close: str, calendar_ref: str,
                         barriers: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return exact-horizon observations, keeping endpoints and paths separate."""
    audit = audit_terminal_intraday(payload, root=root, session=session, as_of=as_of)
    start, cutoff, opened, closed = map(_timestamp, (origin, as_of, session_open, session_close))
    if (not opened <= start < closed or start > cutoff
            or any(t.astimezone(ET).date().isoformat() != session for t in (start, opened, closed))
            or not isinstance(calendar_ref, str) or not calendar_ref.strip()):
        raise ValueError('invalid origin or explicit session window/reference')
    band = None
    if barriers is not None:
        if (not isinstance(barriers, dict)
                or not all(_number(barriers.get(k)) for k in ('lower', 'upper'))
                or not 0 < barriers['lower'] < barriers['upper']
                or not isinstance(barriers.get('source_ref'), str)
                or not barriers['source_ref'].strip()
                or _timestamp(barriers.get('known_at')) > start):
            raise ValueError('invalid or post-origin barrier definition')
        band = {k: barriers[k] for k in ('lower', 'upper', 'known_at', 'source_ref')}
    out = dict(schema='options.exposure_outlook.observed_outcomes/v1', root=root,
               session=session, origin=start.isoformat(), as_of=cutoff.isoformat(),
               mode='retrospective_observation', authority_tier='research',
               can_publish_forecast=False, input_research_admission='not_qualified',
               outcome_known_at=None, source_input_sha256=_digest(payload),
               source_reason_codes=audit['reason_codes'], status='unavailable',
               reason_codes=[], outcomes=[], barriers=band)
    out['session_window'] = dict(open=opened.isoformat(), close=closed.isoformat(),
                                 source_ref=calendar_ref, qualification='caller_declared')
    fatal = sorted(set(audit['reason_codes']) & _FATAL)
    if fatal:
        out['reason_codes'] = fatal
        return out
    evidence = payload['source_evidence']
    clock = evidence.get('assembly_clock')
    served = clock.get('served_at') if isinstance(clock, dict) else None
    observed = None
    if served is not None:
        observed = _timestamp(served)
        if observed > cutoff:
            out['reason_codes'] = ['RESPONSE_OBSERVED_AFTER_CUTOFF']
            return out
        out['outcome_known_at'] = observed.isoformat()
    span = timedelta(minutes=1 if payload['tf'] == '1m' else 5)
    candles = [(terminal_bar_open_utc(b[0]), b) for b in payload['bars']]
    times = [t for t, _ in candles]
    if len(set(times)) != len(times):
        out['reason_codes'] = ['DUPLICATE_BAR_TIME']
        return out
    candles = [(t, b) for t, b in candles if opened <= t and t + span <= closed]
    by_close = {t + span: b for t, b in candles}
    anchor = by_close.get(start)
    if anchor is None:
        out['reason_codes'] = ['ANCHOR_CLOSE_MISSING']
        return out
    out.update(status='observed_outcomes', anchor_price=anchor[4])
    for horizon in _HORIZONS:
        end = closed if horizon == 'close' else start + timedelta(minutes=horizon)
        target = dict(root=root, session=session, origin=start.isoformat(),
                      target_end=end.isoformat(), horizon=horizon, barriers=band,
                      session_window=out['session_window'])
        row = dict(horizon=horizon, target_end=end.isoformat(),
                   duration_minutes=(end-start).total_seconds()/60,
                   target_id='outlook-target:' + _digest(target), observation_id=None,
                   endpoint_status='unavailable', endpoint_price=None, endpoint_return_pct=None,
                   path_status='unavailable', upper_touched=None, lower_touched=None,
                   exited_band=None, endpoint_inside_band=None, first_touch=None,
                   first_touch_interval=None, reason_codes=[])
        out['outcomes'].append(row)
        if end > closed:
            row['reason_codes'] = ['HORIZON_BEYOND_SESSION']
            continue
        if end > cutoff:
            row.update(endpoint_status='pending', reason_codes=['OUTCOME_NOT_MATURE'])
            continue
        if observed is not None and end > observed:
            row['reason_codes'] = ['RESPONSE_PREDATES_OUTCOME']
            continue
        endpoint = by_close.get(end)
        path = [(t, b) for t, b in candles if start <= t and t + span <= end]
        expected = (end-start) / span
        complete = (expected.is_integer() and len(path) == int(expected)
                    and all(t == start + i*span for i, (t, _) in enumerate(path)))
        row['path_status'] = 'complete' if complete else 'incomplete'
        if not complete:
            row['reason_codes'].append('PATH_INCOMPLETE')
        if endpoint is None:
            row['reason_codes'].append('ENDPOINT_CLOSE_MISSING')
        else:
            row.update(endpoint_status='observed', endpoint_price=endpoint[4],
                       endpoint_return_pct=100*(endpoint[4]/anchor[4]-1))
        if band is not None:
            _path_events(row, path, band, anchor[4], start, span, complete)
            if endpoint is not None:
                row['endpoint_inside_band'] = band['lower'] <= endpoint[4] <= band['upper']
        row['observation_id'] = 'outlook-observation:' + _digest(dict(
            target_id=row['target_id'], input_sha256=out['source_input_sha256'],
            observed_fields={k: v for k, v in row.items() if k != 'observation_id'}))
    return out


def _path_events(row: dict[str, Any], path: list[tuple[datetime, list[Any]]],
                 band: dict[str, Any], spot: float, start: datetime,
                 span: timedelta, complete: bool) -> None:
    lower, upper = band['lower'], band['upper']
    upper_seen = spot >= upper or any(b[2] >= upper for _, b in path)
    lower_seen = spot <= lower or any(b[3] <= lower for _, b in path)
    exit_seen = not lower <= spot <= upper or any(b[2] > upper or b[3] < lower for _, b in path)
    row['upper_touched'] = True if upper_seen else (False if complete else None)
    row['lower_touched'] = True if lower_seen else (False if complete else None)
    row['exited_band'] = True if exit_seen else (False if complete else None)
    if not complete:
        return
    if spot >= upper or spot <= lower:
        row['first_touch'] = 'upper' if spot >= upper else 'lower'
        row['first_touch_interval'] = dict(start=start.isoformat(), end=start.isoformat())
        return
    for at, bar in path:
        up, down = bar[2] >= upper, bar[3] <= lower
        if up or down:
            row['first_touch'] = ('upper' if bar[1] >= upper else
                                  'lower' if bar[1] <= lower else
                                  'same_bar_unknown_order' if up and down else
                                  'upper' if up else 'lower')
            row['first_touch_interval'] = dict(start=at.isoformat(), end=(at+span).isoformat())
            return
