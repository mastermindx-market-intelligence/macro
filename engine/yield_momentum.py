"""Display-only yield measurements with captured-source observation qualification.

No fetching, persistence, historical-availability certification or trade authority.
The v1 wire fields remain; calculation_version names the fixed-grid correction.
"""
from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
import json
from typing import Any
import numpy as np
import pandas as pd

SERIES = {'2y': 'us2y', '5y': 'us5y', '10y': 'us10y',
          '20y': 'us20y', '30y': 'us30y'}  # Existing DGS20 -> CCW us20y alias.
HORIZONS = (5, 22, 63)
TURN_LOOKBACK = 1260
ORIGIN_ATTR = 'rate_observations'


def _date(value: Any) -> str | None:
    try:
        stamp = pd.Timestamp(value)
        return None if pd.isna(stamp) else str(stamp.date())
    except (TypeError, ValueError, OverflowError):
        return None


def _finite(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors='coerce').replace([np.inf, -np.inf], np.nan)


def _digest(s: pd.Series) -> str:
    rows = [(pd.Timestamp(t).isoformat(), None if pd.isna(v) else float(v).hex())
            for t, v in _finite(s).items()]
    return sha256(json.dumps(rows, separators=(',', ':')).encode()).hexdigest()


def capture_rate_observations(raw: pd.Series, aligned: pd.Series, *,
                              source_id: str | None, source_column: str,
                              ffill_limit: int | None = 5,
                              source_basis: str = 'captured_source_rows') -> dict:
    """Bind origin to the same source read and alignment, never a later file read.

    The digest is an internal consistency check, not source authentication.
    Date labels are not publication/receipt instants. Payload is bounded to1260 rows.
    """
    raw = _finite(raw[~raw.index.duplicated(keep='last')].sort_index())
    tail = _finite(aligned.iloc[-TURN_LOOKBACK:])
    union = aligned.index.union(raw.index)
    origins = pd.Series([_date(t) if pd.notna(v) else None for t, v in raw.items()],
                        index=raw.index, dtype=object).reindex(union)
    values = raw.reindex(union)
    if ffill_limit:
        origins = origins.ffill(limit=ffill_limit)
        values = values.ffill(limit=ffill_limit)
    origins, values = origins.reindex(tail.index), values.reindex(tail.index)
    dates = [str(o) if pd.notna(o) and pd.notna(v) and v == a else None
             for o, v, a in zip(origins, values, tail)]
    return {'schema': 'yield_observation_origin.v1', 'source_id': source_id,
            'source_column': source_column, 'source_basis': source_basis,
            'source_digest': _digest(raw), 'alignment_digest': _digest(tail),
            'origin_dates': dates}


def _origin(tail: pd.Series, column: str, evidence: Any) -> tuple:
    item = evidence.get(column) if isinstance(evidence, Mapping) else None
    if not isinstance(item, Mapping):
        return None, 'not_provided', None
    if item.get('alignment_digest') != _digest(tail):
        return None, 'frame_mismatch', None
    dates = item.get('origin_dates')
    valid = (item.get('schema') == 'yield_observation_origin.v1'
             and item.get('source_column') == column
             and item.get('source_basis') in ('captured_source_rows', 'caller_override')
             and isinstance(dates, list) and len(dates) == len(tail))
    if valid:
        valid = all(o is None or (isinstance(o, str) and _date(o) == o
                    and o <= _date(t)) for o, t in zip(dates, tail.index))
    if not valid:
        return None, 'invalid_metadata', None
    return dates, 'matched_captured_alignment', item


def _last_observed_context(values: pd.Series) -> dict | None:
    """Dated measured samples, never a claim of fresh or continuously observed momentum."""
    observed = values.dropna()
    if observed.empty:
        return None
    stamp, level = observed.index[-1], float(observed.iloc[-1])
    position = int(values.index.get_loc(stamp))
    out = {'basis': 'latest_two_captured_source_rows_on_retained_grid',
           'as_of': _date(stamp), 'level': round(level, 3),
           'previous_as_of': None, 'previous_level': None, 'change_bp': None,
           'elapsed_calendar_days': None, 'elapsed_grid_intervals': None,
           'age_calendar_days': int((values.index[-1] - stamp).days),
           'age_grid_intervals': len(values) - 1 - position,
           'is_current_grid_row': position == len(values) - 1,
           'historical_availability_qualified': False}
    if len(observed) >= 2:
        previous, previous_level = observed.index[-2], float(observed.iloc[-2])
        change = (level - previous_level) * 100
        out.update(previous_as_of=_date(previous), previous_level=round(previous_level, 3),
                   change_bp=round(change, 1) if np.isfinite(change) else None,
                   elapsed_calendar_days=int((stamp - previous).days),
                   elapsed_grid_intervals=position - int(values.index.get_loc(previous)))
    return out


def _bp_change(values: pd.Series, horizon: int) -> float | None:
    if len(values) <= horizon:
        return None
    end, start = values.iloc[-1], values.iloc[-horizon - 1]
    if pd.isna(end) or pd.isna(start):
        return None
    return round(float(end - start) * 100, 1)


def _turn_watch(values: pd.Series, change_22d_bp: float | None) -> str | None:
    if change_22d_bp is None or len(values) < 60:
        return None
    trailing = values.iloc[-TURN_LOOKBACK:]
    percentile = float((trailing <= trailing.iloc[-1]).mean())
    if percentile >= 0.85 and change_22d_bp <= -12:
        return 'rolldown_forming'
    if percentile >= 0.90:
        return 'extreme_high_watch'
    if percentile <= 0.15 and change_22d_bp >= 12:
        return 'rollup_forming'
    if percentile <= 0.10:
        return 'extreme_low_watch'
    return None


def _series_read(frame: pd.DataFrame, column: str,
                 available_at: Mapping[str, Any] | None, evidence: Any) -> dict:
    source_available = _date((available_at or {}).get(column))
    out = {'source_column': column, 'source_id': None, 'status': 'missing',
           'as_of': None, 'frame_as_of': _date(frame.index[-1]) if len(frame) else None,
           'available_at': source_available,
           'availability_status': 'provided' if source_available else 'not_provided_by_feature_frame',
           'historical_availability_qualified': False, 'observation_origin': 'unverified',
           'origin_status': 'not_provided', 'path_qualified': False,
           'horizon_basis': 'fixed_weekday_grid_intervals',
           'level': None, 'carried_level': None, 'last_observed': None,
           'velocity_bp': {f'{h}d': None for h in HORIZONS},
           'endpoint_dates': {f'{h}d': None for h in HORIZONS},
           'acceleration_bp': None, 'turn_watch': None, 'null_reason': None}
    if column not in frame or frame.empty:
        out['null_reason'] = f'source column {column} unavailable'
        return out
    numeric = _finite(frame[column]).iloc[-TURN_LOOKBACK:]
    index = numeric.index
    valid_grid = (isinstance(index, pd.DatetimeIndex) and not index.hasnans
                  and index.is_unique and index.is_monotonic_increasing
                  and index.tz is None and index.equals(index.normalize())
                  and index.equals(pd.bdate_range(index[0], index[-1])))
    if not valid_grid:
        out.update(status='invalid_grid', null_reason='requires an ordered unique weekday feature grid')
        return out
    dates, origin_status, item = _origin(numeric, column, evidence)
    out['origin_status'] = origin_status
    measured = numeric.copy()
    if dates is not None:
        observed = [o == _date(t) for o, t in zip(dates, index)]
        measured = numeric.where(observed)
        out.update(source_id=item.get('source_id'), source_basis=item['source_basis'],
                   source_digest=item.get('source_digest'))
        out['observation_origin'] = ('captured_source_row' if observed[-1]
                                     else 'carried' if dates[-1] else 'missing')
        out['path_qualified'] = (all(observed) and numeric.notna().all()
                                 and item['source_basis'] == 'captured_source_rows')
        out['path_qualified'] = bool(out['path_qualified'])
        if item['source_basis'] == 'caller_override' and observed[-1]:
            out['observation_origin'] = 'caller_supplied_row'
        if out['observation_origin'] == 'carried':
            out.update(carried_level=float(numeric.iloc[-1]), as_of=dates[-1])
    valid = measured.dropna()  # Dates only; NEVER compact the calculation horizon.
    if dates is not None and item['source_basis'] == 'captured_source_rows':
        out['last_observed'] = _last_observed_context(measured)
    if not valid.empty and out['as_of'] is None:
        out['as_of'] = _date(valid.index[-1])
    if pd.isna(measured.iloc[-1]):
        out.update(status='stale' if not valid.empty or out['carried_level'] is not None else 'missing',
                   null_reason='latest grid value is missing, nonfinite or carried; no new measured momentum')
        return out
    out['level'] = round(float(measured.iloc[-1]), 3)
    for h in HORIZONS:
        if len(measured) > h:
            out['endpoint_dates'][f'{h}d'] = [_date(index[-h - 1]), _date(index[-1])]
        out['velocity_bp'][f'{h}d'] = _bp_change(measured, h)
    if len(measured) > 44:
        current, prior = _bp_change(measured, 22), _bp_change(measured.iloc[:-22], 22)
        if current is not None and prior is not None:
            out['acceleration_bp'] = round(current - prior, 1)
    enough = len(measured) >= 64
    out['status'] = 'available' if enough else 'insufficient_history'
    if not enough:
        out['null_reason'] = 'requires 64 grid points for 63-interval velocity'
    elif not out['path_qualified']:
        out['null_reason'] = 'endpoint comparisons only; complete observed path not qualified'
    if enough and out['path_qualified']:
        out['turn_watch'] = _turn_watch(measured, out['velocity_bp']['22d'])
    return out


def build_yield_momentum(frame: pd.DataFrame, *,
                         available_at: Mapping[str, Any] | None = None,
                         observation_evidence: Mapping[str, Any] | None = None) -> dict:
    """Read the supplied frame and its optional captured-source companion.

    attrs is the explicit inputs -> snapshot handoff, validated against each tail.
    Copies preserve it; edits/slices that invalidate it cannot certify a turn.
    Historical release/receipt times remain unknown even with matched origin.
    """
    evidence = (frame.attrs.get(ORIGIN_ATTR) if observation_evidence is None
                else observation_evidence)
    return {'schema': 'yield_momentum.v1', 'calculation_version': 'fixed_grid_origin.v2',
            'asof': _date(frame.index[-1]) if len(frame.index) else None,
            'display_only': True, 'authority': False, 'can_score': False,
            'can_size': False, 'can_trade': False,
            'caveats': ['Weekday grid intervals are not verified Treasury trading sessions.',
                        'Captured source rows do not certify historical availability.',
                        'Endpoint changes do not prove continuous deceleration or a market turn.'],
            'series': {label: _series_read(frame, column, available_at, evidence)
                       for label, column in SERIES.items()}}
