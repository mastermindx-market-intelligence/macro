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
from pandas.tseries.holiday import AbstractHolidayCalendar, GoodFriday, USFederalHolidayCalendar

SERIES = {'2y': 'us2y', '5y': 'us5y', '10y': 'us10y',
          '20y': 'us20y', '30y': 'us30y'}  # Existing DGS20 -> CCW us20y alias.
HORIZONS = (5, 22, 63)
TURN_LOOKBACK = 1260
ORIGIN_ATTR = 'rate_observations'
HOLIDAY_BASIS = 'us_federal_holidays_plus_good_friday_v1'
# Seat amendment A-RIC-F3-W2 (2026-09-25): FRED DGS* (Treasury CMT) publishes each
# date's value the NEXT business day (~16:15 ET) while the nightly bakes at ~00:00Z,
# the evening of the frame date. Measured over the six bakes 2026-09-22 -> 09-25 the
# frame's last 1-3 weekday rows were ALWAYS carried (e.g. 969883bc: source as_of
# 2026-09-22 vs frame_as_of 2026-09-24), so `path_qualified` was structurally False
# and every tenor null on every nightly. A bounded TRAILING publication lag is an
# expected absence: momentum is then measured at the last captured source row and
# dated there; an interior unexpected absence, or a lag beyond the tolerance, still
# withholds the path exactly as before.
TRAILING_PUBLICATION_LAG_ROWS = 3
LAG_BASIS = 'fred_next_business_day_publication_v1'


class _ExpectedAbsenceCalendar(AbstractHolidayCalendar):
    """US federal holidays plus Good Friday (SIFMA full close; CMT does not print).

    Seat amendment A-RIC-F3-W1 (2026-09-24): measured on origin/main
    data/fred/DGS{2,5,10,20,30}, the 1260-row weekday grid 2021-11-24 -> 2026-09-22
    carries 54 rows = 51 federal holidays + 3 Good Fridays (2022-04-15, 2024-03-29,
    2025-04-18); the federal calendar alone leaves those 3 as unexpected carries on
    every series, this calendar leaves zero.
    """
    rules = USFederalHolidayCalendar.rules + [GoodFriday]


def expected_absent_grid(index: pd.DatetimeIndex) -> list[bool]:
    """Mark each grid date that is an expected absence (US federal holiday or Good Friday).

    Pure helper: no network, clock or I/O; an empty index returns ``[]``. The
    fixed weekday grid itself never carries weekends (``pd.bdate_range``).
    """
    if len(index) == 0:
        return []
    holidays = _ExpectedAbsenceCalendar().holidays(
        start=index[0], end=index[-1])
    holiday_set = set(pd.Timestamp(d).date() for d in holidays)
    return [pd.Timestamp(t).date() in holiday_set for t in index]


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
    # `values` is the measured series on the fixed weekday grid: the < 60 guard and
    # the TURN_LOOKBACK window count GRID INTERVALS (horizon_basis), never observed
    # samples. Only the percentile denominator excludes the NaN rows of expected
    # absences -- otherwise a 1260-row grid with ~58 holiday rows scores each NaN as
    # "not <= latest" and biases the percentile down (~0.92 -> ~0.88), silently
    # withholding extreme_high_watch. Seat amendment A-RIC-F3-W1 (2026-09-24).
    if change_22d_bp is None or len(values) < 60:
        return None
    trailing = values.iloc[-TURN_LOOKBACK:]
    latest = trailing.iloc[-1]
    if pd.isna(latest):
        return None
    observed = trailing.dropna()
    percentile = float((observed <= latest).mean())
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
           'holiday_basis': HOLIDAY_BASIS,
           'expected_absent_grid_rows': 0, 'unexpected_carried_grid_rows': 0,
           'path_qualification_basis': 'captured_source_rows_or_expected_absent',
           'trailing_publication_lag_rows': 0, 'trailing_expected_absent_rows': 0,
           'lag_tolerance_rows': TRAILING_PUBLICATION_LAG_ROWS, 'lag_basis': LAG_BASIS,
           'measurement_origin': 'latest_grid_row',
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
        expected = expected_absent_grid(index)
        qualified_rows = [o or e for o, e in zip(observed, expected)]
        out.update(source_id=item.get('source_id'), source_basis=item['source_basis'],
                   source_digest=item.get('source_digest'))
        out['observation_origin'] = ('captured_source_row' if observed[-1]
                                     else 'carried' if dates[-1] else 'missing')
        out['expected_absent_grid_rows'] = sum(1 for e in expected if e)
        out['unexpected_carried_grid_rows'] = sum(
            1 for o, e in zip(observed, expected) if not o and not e)
        out['path_qualified'] = (all(qualified_rows) and numeric.notna().all()
                                 and item['source_basis'] == 'captured_source_rows')
        out['path_qualified'] = bool(out['path_qualified'])
        if item['source_basis'] == 'caller_override' and observed[-1]:
            out['observation_origin'] = 'caller_supplied_row'
        if out['observation_origin'] == 'carried':
            out.update(carried_level=float(numeric.iloc[-1]), as_of=dates[-1])
    lag_suffix = ''
    if dates is not None and item['source_basis'] == 'captured_source_rows':
        # last_observed describes the FULL retained grid (age, is_current_grid_row).
        out['last_observed'] = _last_observed_context(measured)
        # Trailing run: the maximal suffix of grid rows with no captured source row.
        # `lag_rows` = its unexpected (non-holiday) rows = the publication lag.
        suffix = 0
        for o in reversed(observed):
            if o:
                break
            suffix += 1
        expected_in_suffix = sum(1 for e in expected[len(expected) - suffix:] if e) if suffix else 0
        lag_rows = suffix - expected_in_suffix
        interior_unexpected = out['unexpected_carried_grid_rows'] - lag_rows
        out['trailing_publication_lag_rows'] = lag_rows
        out['trailing_expected_absent_rows'] = expected_in_suffix
        # A lag row is a carried-forward FINITE fill; a nonfinite latest print is a
        # corrupt row, not a publication lag, and stays unqualified as before.
        suffix_is_carried_fill = bool(suffix) and bool(numeric.iloc[-suffix:].notna().all())
        if (0 < lag_rows <= TRAILING_PUBLICATION_LAG_ROWS and interior_unexpected == 0
                and suffix_is_carried_fill):
            # Measure at the last captured source row: drop the whole unobserved
            # suffix (lag rows plus any expected absences inside it). Horizons stay
            # fixed weekday-grid intervals -- they simply end at that captured row.
            measured = measured.iloc[:-suffix]
            index = index[:-suffix]
            out['path_qualified'] = bool(all(qualified_rows[:-suffix])
                                         and numeric.iloc[:-suffix].notna().all())
            out['measurement_origin'] = 'last_captured_source_row'
        elif lag_rows > TRAILING_PUBLICATION_LAG_ROWS:
            lag_suffix = (f'; trailing publication lag {lag_rows} rows exceeds '
                          f'tolerance {TRAILING_PUBLICATION_LAG_ROWS}')
        elif lag_rows > 0 and interior_unexpected > 0:
            lag_suffix = '; interior unexpected absence withholds the path'
    valid = measured.dropna()  # Dates only; NEVER compact the calculation horizon.
    if not valid.empty and out['as_of'] is None:
        out['as_of'] = _date(valid.index[-1])
    if pd.isna(measured.iloc[-1]):
        out.update(status='stale' if not valid.empty or out['carried_level'] is not None else 'missing',
                   null_reason='latest grid value is missing, nonfinite or carried; no new measured momentum'
                   + lag_suffix)
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
        out['null_reason'] = ('endpoint comparisons only; complete observed path not qualified'
                              + lag_suffix)
    if enough and out['path_qualified']:
        # Grid-based series in; expected-absence NaNs are excluded only from the
        # percentile denominator inside _turn_watch (see its comment).
        out['turn_watch'] = _turn_watch(measured, out['velocity_bp']['22d'])
    return out


# --- Y0 (RIC-INCLUDED-CORE): curve convention + endpoint qualification ---------
# Display-tier provenance APPENDED to each v4 series read: this block describes
# the existing endpoints, it never recomputes, renames or re-values them.
QUALIFICATION_VERSION = 'curve_endpoint_qualification.v1'
# FRED DGS* are Treasury constant-maturity yields read off the par curve; a
# column absent from this map has convention None (unknown) -- never defaulted
# to par or zero.
CURVE_CONVENTION = {'us2y': 'par', 'us5y': 'par', 'us10y': 'par',
                    'us20y': 'par', 'us30y': 'par'}
LEVEL_UNIT = 'pct_ann_rate'
CHANGE_UNIT = 'bp'


def _endpoint(numeric, i, dates, observed, expected, item, convention):
    """One dated endpoint with its origin precedence.

    A non-observed endpoint NEVER carries a numeric level: missing is never 0
    and a carry is never a print.
    """
    out = {'date': _date(numeric.index[i]), 'level': None, 'unit': LEVEL_UNIT,
           'curve_convention': convention, 'origin': 'missing',
           'value_state': 'missing', 'quality': [], 'limitations': [],
           'carried_from': None}
    if dates is None:
        # No matched origin evidence: the frame value may be shown, but its
        # observation origin stays unverified and never certifies anything.
        value = numeric.iloc[i]
        out['origin'] = 'unverified'
        if pd.notna(value):
            out['level'] = round(float(value), 3)
            out['value_state'] = 'present'
        else:
            out['value_state'] = 'missing'
        out['limitations'] = ['observation_origin_unverified']
        return out
    if observed[i]:
        out['origin'] = ('caller_supplied_row'
                         if item['source_basis'] == 'caller_override'
                         else 'captured_source_row')
        out['value_state'] = 'present'
        out['level'] = round(float(numeric.iloc[i]), 3)
        return out
    if expected[i]:
        # US federal holiday / Good Friday: an expected absence beats a carry.
        out['origin'] = 'expected_absent'
        out['limitations'] = ['expected_absence_holiday_basis']
        if dates[i]:
            out['value_state'] = 'stale'
            out['quality'] = ['carried']
            out['carried_from'] = dates[i]
        else:
            out['value_state'] = 'missing'
        return out
    if dates[i]:
        # An unexpected carried fill: stale by definition, never a fresh print.
        out['origin'] = 'carried'
        out['value_state'] = 'stale'
        out['quality'] = ['carried']
        out['carried_from'] = dates[i]
        return out
    return out


def _endpoint_provenance(frame, column, evidence, read):
    """The five qualification keys appended to a v4 series read.

    The origin is re-derived with the unchanged ``_origin`` helper; endpoint
    dates come from the unmodified ``read`` (after a trailing-lag trim its end
    date is the last captured row, and positions counted from the start of the
    retained tail are unchanged), so the v4 semantics are described, never
    recomputed. A missing column, an empty frame or an early-returning read
    leaves every endpoint None.
    """
    out = {'curve_convention': CURVE_CONVENTION.get(column),
           'level_unit': LEVEL_UNIT, 'change_unit': CHANGE_UNIT,
           'endpoints': {f'{h}d': None for h in HORIZONS},
           'turn_certified': bool(read['turn_watch'] is not None
                                  and read['path_qualified'] is True
                                  and read.get('source_basis')
                                  == 'captured_source_rows')}
    if (column not in frame or frame.empty
            or not any(isinstance(pair, list)
                       for pair in read['endpoint_dates'].values())):
        # The v4 read returned early (missing column, empty frame, invalid grid,
        # stale or missing latest print) and dated no endpoint: there is nothing
        # to describe, and an undated grid must never be indexed by date.
        return out
    numeric = _finite(frame[column]).iloc[-TURN_LOOKBACK:]
    dates, origin_status, item = _origin(numeric, column, evidence)
    observed = expected = None
    if dates is not None:
        observed = [o == _date(t) for o, t in zip(dates, numeric.index)]
        expected = expected_absent_grid(numeric.index)
    position = {str(stamp.date()): i for i, stamp in enumerate(numeric.index)}
    convention = CURVE_CONVENTION.get(column)
    for h in HORIZONS:
        pair = read['endpoint_dates'][f'{h}d']
        if not (isinstance(pair, list) and len(pair) == 2
                and pair[0] in position and pair[1] in position):
            continue
        start = _endpoint(numeric, position[pair[0]], dates, observed,
                          expected, item, convention)
        end = _endpoint(numeric, position[pair[1]], dates, observed, expected,
                        item, convention)
        if dates is None:
            certified, reason = False, f'origin_{origin_status}'
        elif item['source_basis'] == 'caller_override':
            certified, reason = False, 'caller_override_basis'
        elif (start['origin'] != 'captured_source_row'
              or start['value_state'] != 'present'):
            certified, reason = False, f"start_endpoint_{start['origin']}"
        elif (end['origin'] != 'captured_source_row'
              or end['value_state'] != 'present'):
            certified, reason = False, f"end_endpoint_{end['origin']}"
        elif read['velocity_bp'][f'{h}d'] is None:
            certified, reason = False, 'velocity_unavailable'
        else:
            certified, reason = True, None
        out['endpoints'][f'{h}d'] = {'start': start, 'end': end,
                                     'change_unit': CHANGE_UNIT,
                                     'certified': certified,
                                     'not_certified_reason': reason}
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
    series = {}
    for label, column in SERIES.items():
        read = _series_read(frame, column, available_at, evidence)
        read.update(_endpoint_provenance(frame, column, evidence, read))
        series[label] = read
    return {'schema': 'yield_momentum.v1', 'calculation_version': 'fixed_grid_origin.v4',
            'asof': _date(frame.index[-1]) if len(frame.index) else None,
            'display_only': True, 'authority': False, 'can_score': False,
            'can_size': False, 'can_trade': False,
            'caveats': ['Weekday grid intervals are not verified Treasury trading sessions.',
                        'Captured source rows do not certify historical availability.',
                        'Endpoint changes do not prove continuous deceleration or a market turn.',
                        'Expected absences are US federal holidays and Good Friday only; a carried print on any other weekday still withholds path qualification.',
                        f'A trailing publication lag of at most {TRAILING_PUBLICATION_LAG_ROWS} weekday rows is an expected absence: momentum is then measured and dated at the last captured source row (as_of), never at the frame date.'],
            'series': series,
            'qualification_version': QUALIFICATION_VERSION}


CURVE_ACCOUNTING_SCHEMA = 'curve_accounting.v1'
CURVE_ACCOUNTING_VERSION = 'ric_y1_curve_accounting.v1'
_CURVE_SOURCES = {'us10y': 'DGS10', 'us10y_real': 'DFII10', 'term_premium_10y': 'THREEFYTP10'}
_STALE_CALENDAR_DAYS = {'us10y': 7, 'us10y_real': 7, 'term_premium_10y': 31}
_KW_MODEL_ID = 'kw_fred_threefytp10'
_CURVE_LAW = (
    'KW and ACM term premia are separate models with separate source, version, fit, vintage and maturity; '
    'their disagreement is model disagreement, not a forecast or a signal.',
    'nominal = expected short rate + term premium and nominal ~= real + inflation compensation are two '
    'alternative accounting views of the same yield; they are never added together.',
    'One nominal yield move cannot identify its own cause; conditional alternatives are shown, never a '
    'single attribution.',
)


def _ref_end(d: str | None) -> str | None:
    if d is None:
        return None
    try:
        return _date(pd.Timestamp(d) + pd.DateOffset(years=10))
    except (TypeError, ValueError, OverflowError):
        return None


def _curve_common_meta() -> dict[str, Any]:
    return {
        'observation_precision': 'day',
        'first_public_precision': 'unknown',
        'first_public_evidence': None,
        'seasonal_treatment': 'n/a',
        'rate_index': 'n/a',
        'averaging_law': 'n/a',
        'source_version': None,
        'content_ref': None,
        'admitted_at': None,
        'target_epoch': None,
    }


def _stale_fields(cutoff_str: str | None, obs_date: str | None, column: str) -> dict[str, Any]:
    if cutoff_str is None or obs_date is None:
        return {}
    cutoff_d = _date(cutoff_str)
    if cutoff_d is None:
        return {}
    tol = _STALE_CALENDAR_DAYS.get(column)
    if tol is None:
        return {}
    days = (pd.Timestamp(cutoff_d) - pd.Timestamp(obs_date)).days
    if days <= tol:
        return {}
    return {
        'value_state': 'stale',
        'quality': ('stale',),
        'limitations': (f'stale_beyond_tolerance_{tol}d',),
    }


def _slice_to_cutoff(frame: pd.DataFrame, cutoff_str: str) -> pd.DataFrame:
    cutoff_d = _date(cutoff_str)
    if cutoff_d is None:
        return frame.iloc[:0]
    keep = []
    for idx in frame.index:
        d = _date(idx)
        if d is not None and d <= cutoff_d:
            keep.append(idx)
    if not keep:
        return frame.iloc[:0]
    return frame.loc[keep]


def _latest_finite_column(frame: pd.DataFrame, column: str) -> tuple[float | None, str | None]:
    if column not in frame.columns:
        return None, None
    s = _finite(frame[column])
    valid = s[s.notna()]
    if valid.empty:
        return None, None
    t = valid.index[-1]
    return float(valid.iloc[-1]), _date(t)


def _paired_nominal_real_date(frame: pd.DataFrame) -> tuple[str | None, str | None]:
    has_nom = 'us10y' in frame.columns
    has_real = 'us10y_real' in frame.columns
    nom = _finite(frame['us10y']) if has_nom else pd.Series(dtype=float)
    real = _finite(frame['us10y_real']) if has_real else pd.Series(dtype=float)
    for idx in reversed(frame.index):
        d = _date(idx)
        if d is None:
            continue
        nv = nom.get(idx) if has_nom else np.nan
        rv = real.get(idx) if has_real else np.nan
        if pd.notna(nv) and pd.notna(rv) and np.isfinite(nv) and np.isfinite(rv):
            return d, d
    _, nom_d = _latest_finite_column(frame, 'us10y')
    _, real_d = _latest_finite_column(frame, 'us10y_real')
    return nom_d, real_d


def _finite_on_date(frame: pd.DataFrame, column: str, date_str: str | None) -> float | None:
    if date_str is None or column not in frame.columns:
        return None
    s = _finite(frame[column])
    for t, v in s.items():
        if _date(t) == date_str and pd.notna(v) and np.isfinite(v):
            return float(v)
    return None


def _curve_accounting_shell(
    *,
    cutoff: str | None,
    status: str,
    reason: str | None,
    basis_schema: str | None,
    asof: str | None = None,
) -> dict[str, Any]:
    return {
        'schema': CURVE_ACCOUNTING_SCHEMA,
        'calculation_version': CURVE_ACCOUNTING_VERSION,
        'basis_schema': basis_schema,
        'cutoff': cutoff,
        'asof': asof,
        'status': status,
        'reason': reason,
        'display_only': True,
        'authority': False,
        'can_score': False,
        'can_size': False,
        'can_trade': False,
        'law': list(_CURVE_LAW),
        'observations': {},
        'comparisons': {},
        'accounting_views': [],
        'views_are_alternatives_never_summed': True,
    }


def _curve_accounting(frame: pd.DataFrame, cutoff: Any) -> dict[str, Any]:
    from engine import rates_command_basis as rcb

    if len(frame.index) == 0:
        return _curve_accounting_shell(
            cutoff=None, status='unavailable', reason='empty_frame', basis_schema=None, asof=None
        )
    if cutoff is None:
        cutoff_str = _date(frame.index[-1])
        if cutoff_str is None:
            return _curve_accounting_shell(
                cutoff=None, status='unavailable', reason='empty_frame', basis_schema=None, asof=None
            )
    else:
        cutoff_str = str(cutoff)
    sliced = _slice_to_cutoff(frame, cutoff_str)
    asof = _date(sliced.index[-1]) if len(sliced.index) else None
    common = _curve_common_meta()

    nom_d, real_d = _paired_nominal_real_date(sliced)
    nom_val = _finite_on_date(sliced, 'us10y', nom_d) if nom_d else None
    real_val = _finite_on_date(sliced, 'us10y_real', real_d) if real_d else None

    kw_val, kw_d = _latest_finite_column(sliced, 'term_premium_10y')

    nom_meta = {
        **common,
        'subject': 'UST_10Y_PAR',
        'evidence_class': 'official_measurement',
        'unit': 'pct_ann_rate',
        'target': 'ust_par_yield',
        'basket_or_index': 'UST',
        'tenor': '10y',
        'curve_convention': 'par',
        'reference_start': nom_d,
        'reference_end': _ref_end(nom_d),
        'observation_time': nom_d,
        'source': 'fred:DGS10',
        'model_id': None,
        'vintage': None,
        'rights': 'public_official',
        'limitations': ('observation_origin_unverified',),
        **_stale_fields(cutoff_str, nom_d, 'us10y'),
    }
    real_meta = {
        **common,
        'subject': 'TIPS_10Y_REAL_PAR',
        'evidence_class': 'official_measurement',
        'unit': 'pct_ann_rate',
        'target': 'ust_real_par_yield',
        'basket_or_index': 'TIPS',
        'tenor': '10y',
        'curve_convention': 'real_par',
        'reference_start': real_d,
        'reference_end': _ref_end(real_d),
        'observation_time': real_d,
        'source': 'fred:DFII10',
        'model_id': None,
        'vintage': None,
        'rights': 'public_official',
        'limitations': ('observation_origin_unverified',),
        **_stale_fields(cutoff_str, real_d, 'us10y_real'),
    }
    kw_meta = {
        **common,
        'subject': 'KW_TP_10Y',
        'evidence_class': 'estimated_decomposition',
        'unit': 'pct_ann_rate',
        'target': 'term_premium_kw',
        'basket_or_index': None,
        'tenor': '10y',
        'curve_convention': 'zero',
        'reference_start': kw_d,
        'reference_end': _ref_end(kw_d),
        'observation_time': kw_d,
        'source': 'fred:THREEFYTP10',
        'model_id': _KW_MODEL_ID,
        'vintage': None,
        'rights': 'public_official',
        'limitations': (
            'model_estimate_not_observed',
            'model_fit_unknown',
            'model_vintage_unknown',
            'observation_origin_unverified',
        ),
        **_stale_fields(cutoff_str, kw_d, 'term_premium_10y'),
    }
    acm_meta = {
        **common,
        'subject': 'ACM_TP_10Y',
        'evidence_class': 'estimated_decomposition',
        'unit': 'pct_ann_rate',
        'target': 'term_premium_acm',
        'basket_or_index': None,
        'tenor': '10y',
        'curve_convention': 'zero',
        'reference_start': None,
        'reference_end': None,
        'observation_time': None,
        'source': None,
        'model_id': 'acm_not_admitted',
        'vintage': None,
        'rights': 'unknown',
        'limitations': ('acm_input_not_admitted',),
    }

    ym = build_yield_momentum(sliced)
    s10 = ym['series']['10y']
    m_val = s10['velocity_bp']['22d']
    pair = s10['endpoint_dates']['22d']
    if isinstance(pair, list) and len(pair) == 2:
        s_date, e_date = pair[0], pair[1]
    else:
        s_date, e_date = None, None
        m_val = None
    endpoint_rec = s10['endpoints']['22d']
    move_limits = ['observation_origin_unverified']
    if m_val is not None:
        if endpoint_rec is None:
            move_limits.append('endpoint_not_certified:None')
        elif isinstance(endpoint_rec, dict) and endpoint_rec.get('certified') is not True:
            reason = endpoint_rec.get('not_certified_reason')
            move_limits.append(f'endpoint_not_certified:{reason}')

    r_val = None
    if s_date is not None and e_date is not None:
        start_v = _finite_on_date(sliced, 'us10y_real', s_date)
        end_v = _finite_on_date(sliced, 'us10y_real', e_date)
        if start_v is not None and end_v is not None:
            r_val = round((end_v - start_v) * 100, 1)

    nom_move_meta = {
        **common,
        'subject': 'UST_10Y_PAR_MOVE_22D',
        'evidence_class': 'official_measurement',
        'unit': 'bp',
        'target': 'ust_par_yield_move',
        'basket_or_index': 'UST',
        'tenor': '10y',
        'curve_convention': 'par',
        'reference_start': s_date,
        'reference_end': e_date,
        'observation_time': e_date,
        'source': 'fred:DGS10',
        'model_id': None,
        'vintage': None,
        'rights': 'public_official',
        'limitations': tuple(move_limits),
    }
    real_move_meta = {
        **common,
        'subject': 'TIPS_10Y_REAL_PAR_MOVE_22D',
        'evidence_class': 'official_measurement',
        'unit': 'bp',
        'target': 'ust_real_par_yield_move',
        'basket_or_index': 'TIPS',
        'tenor': '10y',
        'curve_convention': 'real_par',
        'reference_start': s_date,
        'reference_end': e_date,
        'observation_time': e_date,
        'source': 'fred:DFII10',
        'model_id': None,
        'vintage': None,
        'rights': 'public_official',
        'limitations': ('observation_origin_unverified',),
    }

    obs_objects = {
        'nominal_10y': rcb.qualify_observation(nom_val, nom_meta, cutoff_str),
        'real_10y': rcb.qualify_observation(real_val, real_meta, cutoff_str),
        'term_premium_kw_10y': rcb.qualify_observation(kw_val, kw_meta, cutoff_str),
        'term_premium_acm_10y': rcb.qualify_observation(None, acm_meta, cutoff_str),
        'nominal_10y_move_22d': rcb.qualify_observation(m_val, nom_move_meta, cutoff_str),
        'real_10y_move_22d': rcb.qualify_observation(r_val, real_move_meta, cutoff_str),
    }
    comparisons = {
        'inflation_compensation': rcb.compare_qualified(
            obs_objects['nominal_10y'],
            obs_objects['real_10y'],
            rcb.RULES['inflation_compensation.v1'],
        ).to_dict(),
        'term_premium_kw_vs_acm': rcb.compare_qualified(
            obs_objects['term_premium_kw_10y'],
            obs_objects['term_premium_acm_10y'],
            rcb.RULES['term_premium_kw_vs_acm.v1'],
        ).to_dict(),
        'nominal_par_vs_kw_zero': rcb.compare_qualified(
            obs_objects['nominal_10y'],
            obs_objects['term_premium_kw_10y'],
            rcb.RULES['par_vs_zero.v1'],
        ).to_dict(),
        'yield_move_attribution': rcb.compare_qualified(
            obs_objects['nominal_10y_move_22d'],
            obs_objects['real_10y_move_22d'],
            rcb.RULES['yield_move_attribution.v1'],
        ).to_dict(),
    }
    observations = {k: v.to_dict() for k, v in obs_objects.items()}
    any_present = any(o['value_state'] == 'present' for o in observations.values())
    status = 'available' if any_present else 'unavailable'
    reason = None if any_present else 'no_present_observation'
    accounting_views = [
        {
            'view_id': 'expected_short_plus_term_premium',
            'identity': 'nominal = expected_short + term_premium',
            'present': ['term_premium_kw_10y'],
            'not_observed': ['expected_short_10y'],
            'note': (
                'The expected short-rate path is not observed here and is never derived by '
                'subtracting a zero-coupon model premium from a par yield.'
            ),
        },
        {
            'view_id': 'real_plus_inflation_compensation',
            'identity': 'nominal ~= real + inflation_compensation',
            'present': ['real_10y'],
            'comparison': 'inflation_compensation',
            'note': (
                'This compensation is the same quantity as the published 10y breakeven; '
                'it is shown once and never added to it or to the term premium.'
            ),
        },
    ]
    return {
        'schema': CURVE_ACCOUNTING_SCHEMA,
        'calculation_version': CURVE_ACCOUNTING_VERSION,
        'basis_schema': rcb.SCHEMA_VERSION,
        'cutoff': cutoff_str,
        'asof': asof,
        'status': status,
        'reason': reason,
        'display_only': True,
        'authority': False,
        'can_score': False,
        'can_size': False,
        'can_trade': False,
        'law': list(_CURVE_LAW),
        'observations': observations,
        'comparisons': comparisons,
        'accounting_views': accounting_views,
        'views_are_alternatives_never_summed': True,
    }


def build_curve_accounting(frame: pd.DataFrame, *, cutoff: Any = None) -> dict[str, Any]:
    cutoff_out: str | None
    try:
        if cutoff is not None:
            cutoff_out = str(cutoff)
        elif len(frame.index) == 0:
            cutoff_out = None
        else:
            cutoff_out = _date(frame.index[-1])
    except Exception:
        cutoff_out = None
    try:
        return _curve_accounting(frame, cutoff)
    except Exception as exc:
        shell = _curve_accounting_shell(
            cutoff=cutoff_out,
            status='error',
            reason=f'internal_error:{type(exc).__name__}',
            basis_schema=None,
            asof=None,
        )
        return shell
