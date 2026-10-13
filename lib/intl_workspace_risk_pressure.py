"""Independent disclosed pressure fields; no composite country-risk judgment."""
from copy import deepcopy
from math import isclose, isfinite

from lib.intl_workspace_macro import (
    _check_builtin_tree, _registry, _exact, _date, _period, _text,
    _precision, _compatible_zone, _instant, _MEASURE_KEYS,
)

_FIELDS = {
    'country_credit_change': ('bp', 'country_credit_spread'),
    'constituent_breadth_50d': ('percent', 'constituent_breadth'),
    'annual_current_account': ('percent_gdp', 'current_account'),
}
_QUALITIES = {'qualified', 'stale', 'missing', 'denied', 'failed', 'unsupported', 'unknown'}
_PERMISSIONS = {'allowed', 'unknown', 'denied'}
_REASONS = {'stale': 'source_stale', 'failed': 'source_failed',
            'unsupported': 'method_unsupported', 'missing': 'not_supplied',
            'denied': 'value_denied', 'unknown': 'disclosure_unknown'}


def _unknown(field, reason='support_unavailable'):
    return {'field': field, 'quality': 'unknown', 'reason': reason}


def _nonempty(value):
    _text(value, 'text', nullable=False)
    if not value.strip():
        raise ValueError
    return value


def _support(field, support, measure, market_id):
    instrument = measure['instrument']
    if field == 'country_credit_change':
        _exact(support, {'method_ref','scope','instrument_id','market_id','change_start','change_end'}, 'support')
        if (support['scope'] != 'country' or support['instrument_id'] != instrument['id']
                or measure['period'] is None
                or support['change_start'] != measure['period']['start']
                or support['change_end'] != measure['period']['end']):
            raise ValueError
    elif field == 'constituent_breadth_50d':
        _exact(support, {'method_ref','market_id','index_id','membership_asof','membership_ref',
                         'eligible_count','above_count','lookback_sessions'}, 'support')
        if support['index_id'] != instrument['id']:
            raise ValueError
        _nonempty(support['membership_ref'])
        membership = _date(support['membership_asof'])
        if membership is None:
            raise ValueError
        observation = measure['observation_at']
        mp, mz = _precision(membership)
        op, oz = _precision(observation)
        if mp != op or not _compatible_zone(mz, oz) or _instant(membership) > _instant(observation):
            raise ValueError
        eligible, above, lookback = (support[key] for key in ('eligible_count','above_count','lookback_sessions'))
        if (any(type(n) is not int for n in (eligible, above, lookback))
                or eligible <= 0 or not 0 <= above <= eligible or lookback != 50):
            raise ValueError
        if not isclose(measure['value'], above / eligible * 100, rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError
    else:
        _exact(support, {'method_ref','market_id','field_year','vintage','observation_type'}, 'support')
        year = support['field_year']
        if type(year) is not int or not 1 <= year < 9999:
            raise ValueError
        if _date(support['vintage']) is None or support['observation_type'] not in {'actual','estimate','projection'}:
            raise ValueError
        period = measure['period']
        if (period is None or period['start'] != f'{year:04d}-01-01'
                or period['end'] != f'{year+1:04d}-01-01' or period['count'] != 1
                or period['count_basis'] != 'release_periods'):
            raise ValueError
        if support['observation_type'] == 'actual' and measure['observation_at'][:10] < period['end']:
            raise ValueError
    if support['market_id'] != market_id:
        raise ValueError
    _nonempty(support['method_ref'])
    return deepcopy(support)


def _field(field, market_id, measure, support):
    if measure is None:
        return _unknown(field, 'not_supplied')
    try:
        _exact(measure, _MEASURE_KEYS, 'measure')
        quality, metadata, permission = (measure[key] for key in ('quality','metadata','value_permission'))
        if (quality not in _QUALITIES or metadata not in _PERMISSIONS or permission not in _PERMISSIONS):
            raise ValueError
        if metadata != 'allowed':
            return {'field':field, 'quality':'denied' if metadata=='denied' else 'unknown',
                    'reason':'metadata_denied' if metadata=='denied' else 'disclosure_unknown'}
        unit, kind = _FIELDS[field]
        if measure['unit'] != unit:
            raise ValueError
        instrument = measure['instrument']
        _exact(instrument, {'kind','id','market_id'}, 'instrument')
        if instrument['market_id'] != market_id or instrument['kind'] != kind:
            raise ValueError
        _nonempty(instrument['id'])
        period = _period(measure['period'])
        observation = _date(measure['observation_at'])
        calculation = _date(measure['calculation_at'])
        for key in ('source_reference','evidence_key'):
            if measure[key] is not None:
                _nonempty(measure[key])
        value = measure['value']
        if value is not None and (type(value) not in (int,float) or (type(value) is float and not isfinite(value))):
            raise ValueError
        out = {'field':field,'quality':quality,'reason':_REASONS.get(quality),
               'value':None,'unit':unit,'instrument':deepcopy(instrument),'period':period,
               'observation_at':observation,'calculation_at':calculation,
               'source_reference':measure['source_reference'],'evidence_key':measure['evidence_key']}
        if permission != 'allowed':
            out.update(quality='denied' if permission=='denied' else 'unknown',
                       reason='value_denied' if permission=='denied' else 'disclosure_unknown')
            return out
        if quality in {'qualified','stale'}:
            if value is None or observation is None:
                raise ValueError
            _nonempty(measure['source_reference']); _nonempty(measure['evidence_key'])
            # Evidence is validated against the owner metric, never used to
            # overwrite or calculate a replacement financial observation.
            out['support'] = _support(field, support, measure, market_id)
            out['value'] = value
        return out
    except (ValueError, TypeError, KeyError, OverflowError):
        return _unknown(field)


def build_pressure_rows(*, registry, measures, field_support):
    """Retain roster and independent field clocks from supplied admitted records."""
    try:
        for value in (registry, measures, field_support):
            _check_builtin_tree(value)
        markets, _, _ = _registry(registry)
        if type(measures) is not dict or type(field_support) is not dict:
            raise ValueError
        keys = {f'{market["market_id"]}.{field}' for market in markets for field in _FIELDS}
        if not set(measures) <= keys or not set(field_support) <= keys:
            raise ValueError
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
        raise ValueError('invalid_risk_pressure_input') from None
    rows=[]
    for market in markets:
        row=deepcopy(market)
        for field in _FIELDS:
            key=f'{market["market_id"]}.{field}'
            row[field]=_field(field,market['market_id'],measures.get(key),field_support.get(key))
        rows.append(row)
    return rows
