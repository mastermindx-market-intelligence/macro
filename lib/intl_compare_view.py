"""Selected-market endpoint comparison over the disclosed Overview owner.

This consumer does not qualify raw records or disclose interior chart points.
It reuses the existing projection and chronology validators; equality of owner
calculation windows is sufficient only for the endpoint-return table.
"""
from copy import deepcopy

from engine.intl_workspace_overview import _validate_window
from lib.intl_inspector_view import _plain, _validate as _validate_overview

_LEGS = ('local', 'usd', 'fx_contribution')
_IDENTITY = ('slot', 'market_id', 'name_en', 'name_zh', 'index_id', 'index_label')
_CONTEXT = ('horizon', 'currency_basis', 'return_basis', 'source_reference')
_WINDOW = ('start', 'end', 'calendar_policy')
_PUBLIC_REASONS = {'qualification_unknown', 'binding_mismatch', 'missing_record',
                   'not_disclosed', 'not_disclosed_or_unknown', 'source_unknown',
                   'value_denied', 'value_unknown', 'numerical_unavailable',
                   'quality_stale', 'quality_missing', 'quality_denied',
                   'quality_failed', 'quality_unsupported', 'quality_unknown'}


def _validate_input(overview, selected_slots):
    try:
        # Reject subclass hooks before indexing or traversing any supplied object.
        _plain(overview)
        if type(overview) is not dict or type(overview.get('context')) is not dict:
            raise ValueError
        context = {key: overview['context'][key] for key in _CONTEXT}
        # The existing Inspector validates the same disclosed Overview boundary.
        # A fixed nonempty selection is a validation argument, never an ID join.
        _validate_overview(overview, context, 'compare-validation', [])
        if (type(selected_slots) is not list or len(selected_slots) > 4
                or any(type(slot) is not int or slot < 0 for slot in selected_slots)
                or len(set(selected_slots)) != len(selected_slots)):
            raise ValueError
        rows = {row['slot']: row for row in overview['rows']}
        if any(slot not in rows for slot in selected_slots):
            raise ValueError
        for row in rows.values():
            for leg in ('metric', *_LEGS):
                if leg in row:
                    # Preserve strings exactly; delegate chronological geometry
                    # (including nanosecond/timezone precision) to its owner.
                    _validate_window(row[leg].get('window'), required=False)
        return rows
    except (ValueError, KeyError, TypeError, RecursionError) as error:
        raise ValueError('invalid_compare_input') from error


def _metric(row, leg):
    if leg not in row:
        return {'value': None, 'unit': 'percentage_points' if leg == 'fx_contribution' else 'percent',
                'quality': 'unknown', 'reason': 'qualification_unknown', 'window': None}
    metric = deepcopy(row[leg])
    # Only fixed public reason keys cross this presentation boundary.
    if metric['reason'] is not None and metric['reason'] not in _PUBLIC_REASONS:
        metric['reason'] = ('not_disclosed' if metric['quality'] == 'denied'
                            else 'quality_' + metric['quality'])
    return metric


def _row(row):
    if row.get('quality') == 'denied':
        return {'slot': row['slot'], 'quality': 'denied', 'reason': 'metadata_denied'}
    output = {key: row[key] for key in _IDENTITY if key in row}
    output.update({leg: _metric(row, leg) for leg in _LEGS})
    return output


def build_compare_view(overview, *, selected_slots):
    """Compare 0–4 explicitly selected slots without inventing a qualified subset.

    Input must be the actual detached Overview projection for one context.
    Structural validation is not receipt authentication or a new access grant.
    """
    by_slot = _validate_input(overview, selected_slots)
    selected = [by_slot[slot] for slot in selected_slots]
    result = {'context': deepcopy(overview['context']), 'status': 'incomplete_selection',
              'reason': 'insufficient_selection', 'selected_count': len(selected),
              'rows': [_row(row) for row in selected], 'common_window': None,
              'order_slots': [],
              'chart': {'status': 'unavailable', 'reason': 'series_qualification_not_supplied'},
              'benchmark': {'status': 'unavailable', 'reason': 'not_supplied'}}
    if len(selected) < 2:
        return result
    result.update(status='withheld', reason='selection_unqualified')
    if overview['context']['source_reference'] is None or any(
            row.get('metric', {}).get('quality') != 'qualified' for row in selected):
        return result
    windows = [row['metric']['window'] for row in selected]
    if len({tuple(window[key] for key in _WINDOW) for window in windows}) != 1:
        result['reason'] = 'unequal_windows'
        return result
    result.update(status='comparable', reason=None,
                  common_window={key: windows[0][key] for key in _WINDOW},
                  order_slots=[row['slot'] for row in sorted(
                      selected, key=lambda row: (-row['metric']['value'], row['market_id']))])
    return result
