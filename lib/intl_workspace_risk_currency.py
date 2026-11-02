"""Explain the disclosed local/USD currency channel without qualifying raw data."""
from copy import deepcopy
from math import isclose, isfinite

from lib.intl_compare_view import build_compare_view

_CONTEXT = ('horizon', 'currency_basis', 'return_basis', 'source_reference')
_IDENTITY = ('slot', 'market_id', 'name_en', 'name_zh', 'index_id', 'index_label')


def _unavailable(unit='percent'):
    return {'value': None, 'unit': unit, 'quality': 'unknown',
            'reason': 'qualification_unknown', 'window': None}


def _same_price_window(left, right):
    if left is None or right is None:
        return False
    return (all(left[key] == right[key] for key in ('start', 'end', 'calendar_policy'))
            and all(left['endpoint_observations'][key] == right['endpoint_observations'][key]
                    for key in ('price_start', 'price_end')))


def build_currency_channel(overview, *, selected_slot):
    """Derive FX only from an already disclosed, compatible local/USD pair.

    Returns preserve owner metrics exactly. This is a pure explanation over the
    accepted Compare boundary, not an alternative source or permission owner.
    """
    try:
        view = build_compare_view(overview, selected_slots=[selected_slot])
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
        raise ValueError('invalid_currency_channel_input') from None
    row = view['rows'][0]
    context = {key: view['context'][key] for key in _CONTEXT}
    denied = row.get('quality') == 'denied'
    local = row.get('local', _unavailable())
    usd = row.get('usd', _unavailable())
    contribution = row.get('fx_contribution', _unavailable('percentage_points'))
    fx = _unavailable()
    usable = any(metric['quality'] == 'qualified' for metric in (local, usd))
    if not usable:
        context['source_reference'] = None
    out = {
        'slot': selected_slot,
        'market': None if denied else {key: row[key] for key in _IDENTITY if key in row},
        'context': context,
        'local_return': local,
        'usd_return': usd,
        'fx_return_usd_per_local': fx,
        'fx_contribution_pp': contribution,
        'arithmetic_quality': 'partial' if any(
            metric['quality'] == 'qualified' for metric in (local, usd, contribution)) else 'unavailable',
        'reason': 'operands_unavailable',
        'endpoint_policy': None,
        'input_evidence_refs': [],
    }
    if (context['source_reference'] is None
            or local['quality'] != 'qualified' or usd['quality'] != 'qualified'):
        return out
    if contribution['quality'] == 'denied':
        out['reason'] = 'fx_not_disclosed'
        return out
    if not _same_price_window(local['window'], usd['window']):
        out['reason'] = 'unequal_windows'
        return out
    try:
        local_value, usd_value = local['value'], usd['value']
        if (not isfinite(local_value) or not isfinite(usd_value)
                or local_value <= -100 or usd_value < -100):
            raise ValueError
        value = ((1 + usd_value / 100) / (1 + local_value / 100) - 1) * 100
        # A positive gross FX return must not collapse to a total-loss claim.
        if not isfinite(value) or (value == -100 and usd_value != -100):
            raise ValueError
    except (ValueError, OverflowError, ZeroDivisionError):
        out['reason'] = 'numerical_unavailable'
        return out
    fx.update(value=value, quality='qualified', reason=None,
              window=deepcopy(usd['window']), derivation='derived_from_disclosed_returns')
    out['endpoint_policy'] = deepcopy(usd['window'])
    out['input_evidence_refs'] = [
        {'source_reference': context['source_reference'], 'slot': selected_slot, 'leg': leg}
        for leg in ('local', 'usd')]
    if contribution['quality'] != 'qualified':
        out['reason'] = 'contribution_unavailable'
    elif not _same_price_window(contribution['window'], usd['window']):
        out['reason'] = 'unequal_windows'
    else:
        try:
            matches = isclose(contribution['value'], usd_value - local_value,
                              rel_tol=1e-12, abs_tol=1e-12)
        except (ValueError, OverflowError):
            matches = False
        if matches:
            out.update(arithmetic_quality='qualified', reason=None)
        else:
            out['reason'] = 'contribution_mismatch'
    return out
