"""Research-only PAYEMS historical vintage date projection.

Reuses the incumbent release_revision_model._value_at_vintage selection rule.
The Data OS caller must verify the exact original file bytes and source version;
this pure function never reads a file, uses a provider, or sizes trades.

Recorded ALFRED vintage dates are day-granular, not authenticated intraday
availability. Later values and their supersession dates never enter a day view.
"""
from __future__ import annotations

from datetime import date
import math
import re
from typing import Any

import pandas as pd

from engine.neuralweb.market_memory_history import HistoricalExperienceError
from engine.release_revision_model import _value_at_vintage

SOURCE_REF = 'macro_snapshot:fred_vintage/payems_all_vintages.parquet'
SCHEMA = 'market_memory.payems_vintage_date.v1'
_COLUMNS = frozenset(('period', 'realtime_start', 'realtime_end', 'value'))
_HEX = re.compile(r'[a-f0-9]{64}\Z')
MAX_ROWS = 400_000
MAX_PERIODS = 24


def _day(value: Any) -> str:
    if type(value) is not str:
        raise HistoricalExperienceError('explicit date-only cutoff required')
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError()
    except ValueError as exc:
        raise HistoricalExperienceError('cutoff must be canonical ISO calendar date') from exc
    return value


def select_payems_date(
    source: pd.DataFrame,
    calendar_date: str,
    *,
    source_ref: str,
    source_version: str,
    source_sha256: str,
    max_periods: int = 12,
    max_rows: int = MAX_ROWS,
) -> dict[str, Any]:
    """Project values recorded as available by the chosen calendar date.

    source_sha256 is caller-declared evidence: the Data OS descriptor owner,
    not this function, must hash and verify original bytes before trusting it.
    This does not reconstruct an intraday information state, a consensus, or
    today's revised value as an originally available observation.
    """
    day = _day(calendar_date)
    if (source_ref != SOURCE_REF or type(source_version) is not str
            or not re.fullmatch(r'statv1:[a-f0-9]{64}', source_version)
            or type(source_sha256) is not str or not _HEX.fullmatch(source_sha256)):
        raise HistoricalExperienceError('exact PAYEMS owner source reference and provenance required')
    if (type(max_rows) is not int or not 1 <= max_rows <= MAX_ROWS
            or type(max_periods) is not int or not 1 <= max_periods <= MAX_PERIODS):
        raise HistoricalExperienceError('bounded vintage row and period limits required')
    if (not isinstance(source, pd.DataFrame) or set(source.columns) != _COLUMNS
            or len(source.columns) != len(_COLUMNS) or len(source) > max_rows):
        raise HistoricalExperienceError('exact bounded multi-vintage PAYEMS source table required')
    try:
        df = source.copy()
        for column in ('period', 'realtime_start'):
            df[column] = pd.to_datetime(df[column], errors='raise', utc=False)
            if (df[column].isna().any() or df[column].dt.tz is not None
                    or (df[column] != df[column].dt.normalize()).any()):
                raise HistoricalExperienceError('multi-vintage source requires explicit date-only rows')
        # The incumbent loader turns the 9999-12-31 open-ended sentinel into
        # NaT (outside pandas Timestamp bounds). The incumbent selection
        # then uses its established latest-known-start fallback.
        end_original = df['realtime_end'].copy()
        df['realtime_end'] = pd.to_datetime(end_original, errors='coerce', utc=False)
        invalid_end = (end_original.notna()
                       & ~end_original.astype(str).str.startswith('9999-12-31')
                       & df['realtime_end'].isna())
        if invalid_end.any():
            raise HistoricalExperienceError('invalid source revision interval end')
        cutoff = pd.Timestamp(day)
        eligible = df[(df['realtime_start'] <= cutoff) & (df['period'] <= cutoff)].copy()
        reversed_intervals = eligible['realtime_end'].notna() & (
            eligible['realtime_end'] < eligible['realtime_start'])
        if reversed_intervals.any():
            raise HistoricalExperienceError('reversed historical revision interval')
        if (eligible['period'] > eligible['realtime_start']).any():
            raise HistoricalExperienceError('period begins after its supposed first vintage')
        if eligible.duplicated(['period', 'realtime_start']).any():
            raise HistoricalExperienceError('ambiguous duplicate historical source vintage')
        for val in eligible['value'].dropna():
            native = val.item() if hasattr(val, 'item') else val
            if type(native) not in (int, float) or not math.isfinite(native):
                raise HistoricalExperienceError('finite numeric or null historical source value required')
        ordered = eligible.sort_values(['period', 'realtime_start'])
        current = ordered.drop_duplicates(['period'], keep='last').sort_values('period', ascending=False)
        periods = []
        for _, row in current.head(max_periods).iterrows():
            period = pd.Timestamp(row['period'])
            owner_value = _value_at_vintage(eligible, period, cutoff)
            visible_value = float(row['value']) if pd.notna(row['value']) else None
            if ((owner_value is None) != (visible_value is None)
                    or (owner_value is not None and owner_value != visible_value)):
                raise HistoricalExperienceError('incumbent PAYEMS vintage selection disagrees')
            periods.append({
                'period': period.date().isoformat(),
                'realtime_start': pd.Timestamp(row['realtime_start']).date().isoformat(),
                'value': visible_value,
            })
        latest = periods[0] if periods else None
        changed_today = int((eligible['realtime_start'] == cutoff).sum())
        last_vintage = eligible['realtime_start'].max() if not eligible.empty else None
    except HistoricalExperienceError:
        raise
    except (KeyError, ValueError, TypeError, OverflowError, AttributeError) as exc:
        raise HistoricalExperienceError('invalid bounded historical PAYEMS vintage source') from exc
    return {
        'schema': SCHEMA,
        'mode': 'RETROSPECTIVE_EXPLORATORY',
        'calendar_date': day,
        'status': 'OBSERVED' if latest is not None else 'NO_RETAINED_VINTAGE_AT_CUTOFF',
        'latest_period': latest['period'] if latest else None,
        'latest_value': latest['value'] if latest else None,
        'latest_vintage_start': latest['realtime_start'] if latest else None,
        'periods': periods,
        'available_periods': len(current),
        'vintage_records_on_selected_date': changed_today,
        'source_last_recorded_vintage': last_vintage.date().isoformat() if last_vintage is not None else None,
        'source_recorded_through_cutoff': bool(not eligible.empty),
        'source_current_to_selected_date_proven': False,
        'source_ref': SOURCE_REF,
        'source_version': source_version,
        'source_sha256': source_sha256,
        'source_sha256_verified_by_projection': False,
        'source_units_independently_verified': False,
        'intraday_publication_time_verified': False,
        'point_in_time_trading_eligible': False,
        'full_historical_macro_universe': False,
        'basis': 'ALFRED_RECORDED_VINTAGE_DATE_ONLY',
        'limits': {'max_periods': max_periods, 'source_rows': max_rows},
    }
