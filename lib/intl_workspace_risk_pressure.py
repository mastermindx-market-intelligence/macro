"""Independent disclosed pressure fields; no composite country-risk judgment."""
import re
from copy import deepcopy
from datetime import date, datetime
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
# Closed statistical-period variant for one Eurostat EA21 annual source identity.
# It is an additional closed shape, not a relaxation: no other field, adapter,
# country, instrument or method may enter this branch.
_STATISTICAL_KEYS = {'method_ref', 'market_id', 'field_year', 'vintage',
                     'observation_type', 'observation_clock_basis', 'dataset_updated_at'}
_STATISTICAL_INSTRUMENT_ID = 'TIPSBP20/A/PC_GDP/CA/S1/S1/BAL/EXT_EA21/NSA/EA21'
_STATISTICAL_METHOD_REF = (
    'docs/INTERNATIONAL_MACRO_DATA_CONTRACT.md#official-eurostat-ea21-annual-current-account'
)
_OFFSET_TIMESTAMP = re.compile(
    r'^(?P<day>[0-9]{4}-[0-9]{2}-[0-9]{2})'
    r'T(?P<clock>[0-9]{2}:[0-9]{2}:[0-9]{2})(?:\.(?P<fraction>[0-9]{1,6}))?'
    r'(?P<zone>Z|[+-][0-9]{2}:?[0-9]{2})$'
)


def _unknown(field, reason='support_unavailable'):
    return {'field': field, 'quality': 'unknown', 'reason': reason}


def _nonempty(value):
    _text(value, 'text', nullable=False)
    if not value.strip():
        raise ValueError
    return value


def _offset_timestamp(value):
    """Parse an offset-aware ISO timestamp without rewriting the source string."""
    if type(value) is not str:
        raise ValueError
    match = _OFFSET_TIMESTAMP.match(value)
    if match is None:
        raise ValueError
    zone = match.group('zone')
    if zone == 'Z':
        zone = '+00:00'
    elif ':' not in zone:
        zone = f'{zone[:3]}:{zone[3:]}'
    clock = match.group('clock')
    fraction = match.group('fraction')
    if fraction:
        # Pad to microseconds so the parse does not depend on the runtime's
        # accepted fractional-second precision.
        clock = f'{clock}.{fraction.ljust(6, "0")}'
    try:
        moment = datetime.fromisoformat(f"{match.group('day')}T{clock}{zone}")
    except ValueError:
        raise ValueError from None
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError
    return moment


def _statistical_annual_support(support, measure, market_id):
    """Closed Eurostat EA21 annual statistical-period support."""
    _exact(support, _STATISTICAL_KEYS, 'support')
    if (support['observation_type'] != 'statistical'
            or support['vintage'] is not None
            or support['observation_clock_basis'] != 'period_end'):
        raise ValueError
    if market_id != 'EZ' or support['market_id'] != 'EZ':
        raise ValueError
    if support['method_ref'] != _STATISTICAL_METHOD_REF:
        raise ValueError
    instrument = measure['instrument']
    if (instrument['kind'] != 'current_account' or instrument['market_id'] != 'EZ'
            or instrument['id'] != _STATISTICAL_INSTRUMENT_ID):
        raise ValueError
    year = support['field_year']
    if type(year) is not int or not 1 <= year < 9999:
        raise ValueError
    period = measure['period']
    if (period is None or period['start'] != f'{year:04d}-01-01'
            or period['end'] != f'{year+1:04d}-01-01' or period['count'] != 1
            or period['count_basis'] != 'release_periods'):
        raise ValueError
    if measure['observation_at'] != f'{year:04d}-12-31':
        raise ValueError
    # The dataset clock is a separately supplied offset-aware source-update stamp. It is never a
    # vintage, an observation or a calculation date; only its local calendar
    # date is compared with the economic period end.
    if _offset_timestamp(support['dataset_updated_at']).date() < date(year, 12, 31):
        raise ValueError
    return deepcopy(support)


def _support(field, support, measure, market_id):
    instrument = measure['instrument']
    if (field == 'annual_current_account' and type(support) is dict
            and support.get('observation_type') == 'statistical'):
        return _statistical_annual_support(support, measure, market_id)
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
