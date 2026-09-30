"""Project the existing FX kinematics table; never compute or score market moves.

This is an additive display member of the existing forex/latest.json publication.
The producer chooses each metric's last non-null reading independently and returns
only its maximum index date. That date is NOT an observation date for every field.
Value completeness below says nothing about freshness, tradability or confidence.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from datetime import date
import math
from numbers import Real
import re
from typing import Any


_FIELDS = {
    'return_short': 'lit_1d_pct', 'return_medium': 'lit_5d_pct',
    'return_long': 'lit_20d_pct', 'velocity_z': 'vel_z',
    'acceleration_z': 'accel_z', 'volatility_percentile': 'rvol_pctile',
    'residual_return': 'resid_5d_pct',
}


def _positive_int(value: object) -> bool:
    return type(value) is int and value > 0


def _metric_definitions(cfg: object) -> dict[str, dict] | None:
    # Do not maintain a second default-configuration owner. The real build passes
    # its explicit config. Missing/ambiguous windows withhold the optional member.
    if not isinstance(cfg, Mapping):
        return None
    regime = cfg.get('regime')
    if not isinstance(regime, Mapping) or regime.get('enabled') is not True:
        return None
    kin = regime.get('kinematics')
    if not isinstance(kin, Mapping):
        return None
    windows = kin.get('lit_windows_d')
    if (not isinstance(windows, list) or len(windows) != 3
            or not all(_positive_int(w) for w in windows)
            or not windows[0] < windows[1] < windows[2]):
        return None
    named = {'rvol_window_d': kin.get('rvol_window_d'),
             'rvol_pctile_lookback_d': kin.get('rvol_pctile_lookback_d'),
             'z_lookback_d': regime.get('z_lookback_d'),
             'z_min_periods': regime.get('z_min_periods'),
             'ewma_halflife_d': regime.get('ewma_halflife_d')}
    if (not all(_positive_int(v) for v in named.values())
            or named['z_min_periods'] > named['z_lookback_d']):
        return None
    definitions = {}
    for key, window in zip(('return_short', 'return_medium', 'return_long'), windows):
        definitions[key] = {'source_field': _FIELDS[key], 'unit': 'percent',
                            'basis': 'currency_vs_usd', 'window_observations': window}
    for key in ('velocity_z', 'acceleration_z'):
        definitions[key] = {'source_field': _FIELDS[key], 'unit': 'z_score',
                            'basis': 'currency_vs_usd', 'window_observations': 5,
                            'z_lookback_observations': named['z_lookback_d'],
                            'z_min_periods': named['z_min_periods'],
                            'ewma_halflife_observations': named['ewma_halflife_d']}
    definitions['volatility_percentile'] = {
        'source_field': _FIELDS['volatility_percentile'], 'unit': 'fraction',
        'basis': 'currency_vs_usd', 'window_observations': named['rvol_window_d'],
        'percentile_lookback_observations': named['rvol_pctile_lookback_d']}
    definitions['residual_return'] = {
        'source_field': _FIELDS['residual_return'], 'unit': 'percent',
        'basis': 'ex_dollar_residual', 'window_observations': 5}
    return definitions


def _calendar_date(value: object) -> str | None:
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return None


def _value(raw: object, key: str) -> tuple[float | None, str]:
    if raw is None:
        return None, 'missing'
    if isinstance(raw, bool) or not isinstance(raw, Real):
        return None, 'invalid'
    try:
        number = float(raw)
    except (OverflowError, ValueError, TypeError):
        return None, 'invalid'
    if (not math.isfinite(number)
            or (key == 'volatility_percentile' and not 0 <= number <= 1)
            or (key in ('return_short', 'return_medium', 'return_long', 'residual_return') and number < -100)):
        return None, 'invalid'
    return number, 'available'


def project_kinematics(table: object, cfg: object) -> dict[str, Any]:
    """Return JSON-safe values, definitions and limitations without mutating inputs.

    No clock, file, network, persistence, fallback numeric value or market-state
    setter is present. Unknown clocks remain unknown even for a complete row.
    """
    out: dict[str, Any] = {
        'version': 1, 'producer': 'engine.forex_regime.fx_kinematics_table',
        'display_only': True, 'value_status': 'unavailable',
        'basis': 'currency_vs_usd',
        'positive_direction': 'currency_appreciation_vs_usd',
        'table_as_of': None, 'date_basis': 'producer_max_index',
        'freshness': 'unknown', 'metric_dates_available': False,
        'limitations': ['last_non_null', 'per_metric_dates_unavailable',
                        'observation_windows_not_calendar_days',
                        'coincident_not_a_forecast', 'correlated_metrics_not_independent_votes'],
        'metrics': {}, 'rows': [], 'issues': [], 'reference_rows_excluded': [],
    }
    definitions = _metric_definitions(cfg)
    if definitions is None:
        out['issues'].append('invalid_configuration')
        return out
    out['metrics'] = definitions
    if not isinstance(table, Mapping) or not table:
        out['issues'].append('table_unavailable')
        return out
    out['table_as_of'] = _calendar_date(table.get('as_of'))
    if out['table_as_of'] is None:
        out['issues'].append('table_date_unavailable')
        return out
    sources = table.get('rows')
    if not isinstance(sources, list) or not sources:
        out['issues'].append('rows_unavailable')
        return out
    candidates = []
    for source in sources:
        # The producer's USD row is the broad-dollar index, not USD versus USD.
        # Excluding that separate reference is not a missing currency observation.
        if (isinstance(source, Mapping) and isinstance(source.get('ccy'), str)
                and source['ccy'] == 'USD'):
            if 'USD' not in out['reference_rows_excluded']:
                out['reference_rows_excluded'].append('USD')
            continue
        if (not isinstance(source, Mapping) or not isinstance(source.get('ccy'), str)
                or not re.fullmatch(r'[A-Z]{3}', source['ccy'])):
            out['issues'].append('invalid_currency_row')
            continue
        candidates.append(source)
    counts = Counter(row['ccy'] for row in candidates)
    seen = set()
    available = 0
    for source in candidates:
        ccy = source['ccy']
        if ccy in seen:
            continue
        seen.add(ccy)
        conflict = counts[ccy] != 1
        row = {'ccy': ccy, 'values': {}, 'availability': {},
               'observed_at': {key: None for key in _FIELDS}}
        if conflict:
            out['issues'].append('duplicate_currency:' + ccy)
        for key, source_field in _FIELDS.items():
            value, status = (None, 'identity_conflict') if conflict else _value(source.get(source_field), key)
            row['values'][key] = value
            row['availability'][key] = status
            available += status == 'available'
        out['rows'].append(row)
    expected = len(out['rows']) * len(_FIELDS)
    if available:
        out['value_status'] = 'complete' if available == expected and not out['issues'] else 'partial'
    return out
