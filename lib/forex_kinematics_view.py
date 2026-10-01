"""Project the existing FX kinematics table; never compute or score market moves.

This is an additive display member of the existing forex/latest.json publication.
The producer chooses each metric's last non-null reading independently. R13 also
supplies those derived-series index dates; older producers supply only the table's
maximum index date. Neither is a vendor observation or publication timestamp.
Value and calculation-date completeness say nothing about source freshness,
tradability, synchronized source observations or confidence.
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
        'basis': 'upstream_residual_index', 'window_observations': 5,
        'adjustment_evidence_field': 'residual_adjustment'}
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


def _project_calculation_clock(source: Mapping, row: dict, table_date: str) -> int:
    """Copy validated selected-index dates; never turn them into source freshness.

    Clock defects are separate from numeric completeness. A date cannot rescue a
    missing value, and a bad date cannot erase a separately valid numeric value.
    """
    row['calculated_through'] = {key: None for key in _FIELDS}
    row['index_relation'] = {key: 'unknown' for key in _FIELDS}
    row['normalized_input_dates'] = {'close': None, 'residual_return': None}
    row['clock_issues'] = []
    clock = source.get('calculation_clock')
    if (not isinstance(clock, Mapping) or type(clock.get('version')) is not int
            or clock['version'] != 1 or not isinstance(clock.get('basis'), str)
            or clock['basis'] != 'derived_series_index'
            or not isinstance(clock.get('selected_index_dates'), Mapping)):
        row['clock_issues'].append('calculation_clock_unavailable')
        return 0
    selected = clock['selected_index_dates']
    dated = 0
    for key, field in _FIELDS.items():
        if row['availability'][key] != 'available':
            continue
        stamp = _calendar_date(selected.get(field))
        if stamp is None or stamp > table_date:
            row['clock_issues'].append('invalid_or_missing_calculation_date:' + key)
            continue
        row['calculated_through'][key] = stamp
        row['index_relation'][key] = 'at_table_date' if stamp == table_date else 'before_table_date'
        dated += 1
    inputs = clock.get('normalized_input_dates')
    if isinstance(inputs, Mapping) and any(value == 'available' for value in row['availability'].values()):
        for key in row['normalized_input_dates']:
            stamp = _calendar_date(inputs.get(key))
            if stamp is not None and stamp <= table_date:
                row['normalized_input_dates'][key] = stamp
    return dated


def _project_residual_adjustment(source: Mapping, row: dict) -> dict[str, Any]:
    """Describe how this selected value was constructed, not its market direction."""
    out = {'status': 'unverified', 'window_observations': 5, 'window_start': None,
           'window_end': None, 'counts': None, 'carried_driver_observations': None}
    if row['availability']['residual_return'] != 'available':
        out['status'] = 'unavailable'
        return out
    receipt = source.get('residual_adjustment')
    if not isinstance(receipt, Mapping):
        return out
    producer, ccy, pair = (receipt.get(k) for k in ('producer', 'ccy', 'pair'))
    if (type(receipt.get('version')) is not int or receipt['version'] != 1
            or not isinstance(producer, str) or producer != 'engine.forex_signals.orthogonalize'
            or not isinstance(ccy, str) or ccy != row['ccy']
            or not isinstance(pair, str) or pair not in (ccy + 'USD', 'USD' + ccy)
            or type(receipt.get('window_observations')) is not int
            or receipt['window_observations'] != 5):
        return out
    start, end = (_calendar_date(receipt.get(k)) for k in ('window_start', 'window_end'))
    if not start or not end or start >= end or end != row['calculated_through']['residual_return']:
        return out
    counts = receipt.get('counts')
    names = {'adjusted', 'raw_fallback', 'zero_filled', 'unavailable'}
    carried = receipt.get('carried_driver_observations')
    if (not isinstance(counts, Mapping) or set(counts) != names
            or any(type(v) is not int or not 0 <= v <= 5 for v in counts.values())
            or sum(counts.values()) != 5 or type(carried) is not int
            or not 0 <= carried <= counts['adjusted']):
        return out
    status = ('unverified' if counts['unavailable'] else
              'input_gaps' if counts['zero_filled'] else
              'adjusted' if counts['adjusted'] == 5 else
              'raw_fallback' if counts['raw_fallback'] == 5 else 'mixed')
    out.update(status=status, window_start=start, window_end=end,
               counts=dict(counts), carried_driver_observations=carried)
    return out


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
        'calculation_date_status': 'unavailable',
        'calculation_date_basis': 'derived_series_index',
        'limitations': ['last_non_null', 'per_metric_dates_unavailable',
                        'calculation_index_is_not_source_observation_or_availability',
                        'normalized_inputs_can_contain_filled_values',
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
    dated = 0
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
        dated += _project_calculation_clock(source, row, out['table_as_of'])
        row['residual_adjustment'] = _project_residual_adjustment(source, row)
        out['rows'].append(row)
    expected = len(out['rows']) * len(_FIELDS)
    if available:
        out['value_status'] = 'complete' if available == expected and not out['issues'] else 'partial'
    if dated:
        out['calculation_date_status'] = 'complete' if dated == expected and not out['issues'] else 'partial'
    return out
