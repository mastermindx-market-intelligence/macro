"""Pure projection of supplied reconstruction history and independent disclosures."""
from copy import deepcopy
import json
import math
import re

from lib.intl_workspace_macro import (
    _check_builtin_tree, _compatible_zone, _date, _destination, _enum, _exact,
    _instant, _parse_date, _precision, _text,
)

_READ_STATES = {'ready', 'empty', 'missing', 'failed', 'invalid', 'unsupported'}
_PERMISSIONS = {'allowed', 'denied', 'unknown'}
_SCORES = ('growth_score', 'inflation_score')
_TRACK_FIELDS = ('market_id', 'graded_count', 'alert_count', 'sample_dates',
                 'precision', 'hit_rate', 'lift', 'false_alarms', 'drawdowns', 'qualification_notes')


def _shape(value, keys):
    _exact(value, keys.split(), 'history')


def _nonfinite(value):
    if type(value) is float and not math.isfinite(value):
        raise ValueError
    if type(value) is dict:
        for child in value.values():
            _nonfinite(child)
    elif type(value) is list:
        for child in value:
            _nonfinite(child)


def _number(value):
    if value is not None and type(value) not in {int, float}:
        raise ValueError


def _required_date(value):
    _text(value, 'date', nullable=False)
    _date(value, month_allowed=True)


def _validate(context, history_read, turn_events, track_record, capabilities, destinations):
    for value in (context, history_read, turn_events, track_record, capabilities, destinations):
        _check_builtin_tree(value)
        _nonfinite(value)
    _shape(context, 'selected_market horizon currency_basis return_basis')
    _text(context['selected_market'], 'selected market')
    for key in ('horizon', 'currency_basis'):
        _text(context[key], key, nullable=False)
    if context['return_basis'] != 'price':
        raise ValueError
    _shape(history_read, 'status market_id artifact_ref read_at method_ref identity points')
    _enum(history_read['status'], _READ_STATES, 'read status')
    for key in ('market_id', 'artifact_ref', 'method_ref'):
        _text(history_read[key], key)
    ref = history_read['artifact_ref']
    if ref is not None and (not re.fullmatch(r'[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*', ref)
                            or any(part in {'.', '..'} for part in ref.split('/'))):
        raise ValueError
    clock = history_read['read_at']
    if clock is not None:
        parsed = _parse_date(clock, False)
        if parsed is None or parsed[1] != 'timestamp' or not parsed[2]:
            raise ValueError
    points = history_read['points']
    if type(points) is not list or (history_read['status'] == 'ready') != bool(points):
        raise ValueError
    identity = history_read['identity']
    if history_read['status'] in {'ready', 'empty'}:
        _text(history_read['market_id'], 'read market', nullable=False)
        _shape(identity, 'market_id unit return_basis universe method_ref')
        for key in ('market_id', 'unit', 'return_basis'):
            _text(identity[key], key, nullable=False)
        for key in ('universe', 'method_ref'):
            _text(identity[key], key)
        if (identity['market_id'] != history_read['market_id']
                or identity['return_basis'] != context['return_basis']
                or identity['method_ref'] != history_read['method_ref']):
            raise ValueError
    elif identity is not None:
        raise ValueError
    previous = None
    for point in points:
        _shape(point, 'observation_at growth_score inflation_score')
        current = point['observation_at']
        _required_date(current)
        for key in _SCORES:
            _number(point[key])
        if previous is not None:
            precision, zone = _precision(current)
            prior_precision, prior_zone = _precision(previous)
            if (precision != prior_precision or not _compatible_zone(zone, prior_zone)
                    or _instant(current) <= _instant(previous)):
                raise ValueError
        previous = current
    if type(turn_events) is not list:
        raise ValueError
    for event in turn_events:
        _shape(event, 'market_id event_date code text_en text_zh evidence_ref source_reference')
        for key, value in event.items():
            _text(value, key, nullable=False)
        _required_date(event['event_date'])
    if track_record is not None:
        _exact(track_record, (*_TRACK_FIELDS, 'read_health'), 'track record')
        _text(track_record['market_id'], 'track market', nullable=False)
        _enum(track_record['read_health'], {'qualified', 'failed', 'missing', 'invalid', 'unsupported'}, 'read health')
        for key in ('graded_count', 'alert_count'):
            value = track_record[key]
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError
            if track_record['read_health'] == 'qualified' and value is None:
                raise ValueError
        dates = track_record['sample_dates']
        if dates is not None:
            if type(dates) is not list:
                raise ValueError
            for value in dates:
                _required_date(value)
        for key in ('precision', 'hit_rate', 'lift', 'false_alarms', 'drawdowns'):
            _number(track_record[key])
        _text(track_record['qualification_notes'], 'qualification notes')
    _shape(capabilities, 'history_source events track_record snapshot_compare')
    for domain in ('history_source', 'events', 'track_record'):
        grant = capabilities[domain]
        _shape(grant, 'metadata value')
        for key in grant:
            _enum(grant[key], _PERMISSIONS, 'permission')
        if grant['value'] == 'allowed' and grant['metadata'] != 'allowed':
            raise ValueError
    compare = capabilities['snapshot_compare']
    _shape(compare, 'left_observation_at right_observation_at')
    left, right = compare['left_observation_at'], compare['right_observation_at']
    if (left is None) != (right is None):
        raise ValueError
    if left is not None:
        _required_date(left)
        _required_date(right)
    if type(destinations) is not dict or not set(destinations) <= {'as_known', 'track_record', 'revisions'}:
        raise ValueError
    for key, entry in destinations.items():
        if _destination(entry) != key:
            raise ValueError


def _events(selected, rows, grant):
    result = dict(status='unavailable', completeness='selected_market_attached_only', reason=None, records=[])
    if grant['metadata'] != 'allowed':
        result.update(status=grant['metadata'], completeness=None,
                      reason='metadata_denied' if grant['metadata'] == 'denied' else 'disclosure_unknown')
    elif selected is None:
        result['reason'] = 'market_not_selected'
    elif grant['value'] != 'allowed':
        result.update(status=grant['value'], reason='value_'+grant['value'])
    else:
        matching = [row for row in rows if row['market_id'] == selected]
        if not matching:
            result['reason'] = 'events_not_supplied' if not rows else 'wrong_market'
        else:
            result['status'] = 'available'
            result['records'] = [{**{k: v for k, v in row.items() if k != 'source_reference'},
                                  'history_kind': 'recomputed'} for row in matching]
    return result


def _track(selected, source, grant, destination):
    result = dict(status='unavailable', reason=None, destination=destination,
                  **{key: None for key in _TRACK_FIELDS})
    if grant['metadata'] != 'allowed':
        result.update(status=grant['metadata'],
                      reason='metadata_denied' if grant['metadata'] == 'denied' else 'disclosure_unknown')
    elif source is None:
        result['reason'] = 'not_supplied'
    elif selected is None:
        result['reason'] = 'market_not_selected'
    elif source['market_id'] != selected:
        result['reason'] = 'wrong_market'
    elif source['read_health'] != 'qualified':
        result['reason'] = 'read_health_'+source['read_health']
    elif grant['value'] != 'allowed':
        result.update(status=grant['value'], reason='value_'+grant['value'],
                      market_id=source['market_id'], sample_dates=source['sample_dates'])
    else:
        result.update(status='available', **{key: source[key] for key in _TRACK_FIELDS})
    return result


def _comparison(result, context, grant, query):
    points = result['points']
    left_at, right_at = query['left_observation_at'], query['right_observation_at']
    left = next((p for p in points if p['observation_at'] == left_at), None)
    right = next((p for p in points if p['observation_at'] == right_at), None)
    out = dict(eligible=False, reason=None, viewed_through='current_reconstruction',
               available_dates=[p['observation_at'] for p in points], left=left, right=right)
    status, identity = result['source_read_status'], result['identity']
    if grant['metadata'] != 'allowed':
        reason = 'metadata_denied' if grant['metadata'] == 'denied' else 'disclosure_unknown'
    elif grant['value'] != 'allowed':
        reason = 'value_'+grant['value']
    elif status == 'wrong_market':
        reason = 'wrong_market'
    elif status == 'unbound':
        reason = 'market_not_selected'
    elif status in {'missing', 'failed', 'invalid', 'unsupported', 'empty'}:
        reason = 'source_'+status
    elif left_at is None:
        reason = 'not_requested'
    elif left is None or right is None:
        reason = 'observation_not_present'
    elif left_at == right_at:
        reason = 'same_observation'
    elif identity is None or any(not identity[key] for key in ('market_id', 'unit', 'return_basis', 'universe', 'method_ref')):
        reason = 'comparability_not_established'
    elif identity['market_id'] != context['selected_market'] or identity['return_basis'] != context['return_basis']:
        reason = 'comparability_not_established'
    elif any(point[key] is None for point in (left, right) for key in _SCORES):
        reason = 'gap_or_null_observation'
    else:
        reason = None
        out['eligible'] = True
    out['reason'] = reason
    return out


def build_history_section(*, context, history_read, turn_events, track_record, capabilities, destinations):
    """Apply supplied grants; never read, grant, reconstruct or write history."""
    try:
        _validate(context, history_read, turn_events, track_record, capabilities, destinations)
        selected = context['selected_market']
        grant = capabilities['history_source']
        read_market = history_read['market_id']
        bound = selected is not None and read_market is not None and selected == read_market
        if grant['metadata'] != 'allowed':
            status = grant['metadata']
        elif selected is None:
            status = 'unbound'
        elif read_market is not None and selected != read_market:
            status = 'wrong_market'
        else:
            status = history_read['status']
        source_metadata = grant['metadata'] == 'allowed' and bound
        source_ref = history_read['artifact_ref'] if source_metadata else None
        acquired = history_read['read_at'] if source_metadata else None
        method = history_read['method_ref'] if source_metadata else None
        identity = history_read['identity'] if source_metadata else None
        points, gaps = [], []
        if source_metadata and status == 'ready':
            for point in history_read['points']:
                if grant['value'] == 'allowed':
                    points.append(point)
                    gaps.extend(dict(observation_at=point['observation_at'], field=key, reason='null_observation')
                                for key in _SCORES if point[key] is None)
                else:
                    points.append(dict(observation_at=point['observation_at'], growth_score=None, inflation_score=None))
        def destination(key):
            return destinations.get(key, {}).get('destination')
        result = dict(mode='recomputed', selected_market=selected, source_read_status=status,
                      source_reference=source_ref,
                      source_reference_kind='relative_reconstruction_artifact' if source_ref is not None else None,
                      acquisition_at=acquired, acquisition_kind='read_clock' if acquired is not None else None,
                      method_ref=method, identity=identity, points=points, gaps=gaps,
                      events=_events(selected, turn_events, capabilities['events']),
                      as_known=dict(available=False, reason='immutable_vintages_not_supplied', destination=destination('as_known')),
                      snapshot_compare=None,
                      revisions=dict(status='unavailable', reason='no_linked_prior_versions', records=[], destination=destination('revisions')),
                      track_record=_track(selected, track_record, capabilities['track_record'], destination('track_record')))
        result['snapshot_compare'] = _comparison(result, context, grant, capabilities['snapshot_compare'])
        detached = deepcopy(result)
        json.dumps(detached, allow_nan=False)
        return detached
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
        raise ValueError('invalid_history_section_input') from None
