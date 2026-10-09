"""Independent counterexamples for the pure history projection helper.

Uses the real helper and Macro validators. Closed 3-sentinel inject mapping only;
never eval fixture text. Builtin JSON trees only.
"""
from copy import deepcopy
import json
import math

import pytest

from lib.intl_workspace_history import build_history_section
from lib.intl_workspace_macro import _destination, _parse_date


PUBLIC_ERROR = 'invalid_history_section_input'
SENTINELS = {"float('nan')": float('nan'), "float('inf')": float('inf'), 'object()': object()}
OUTPUT_KEYS = (
    'mode', 'selected_market', 'source_read_status', 'source_reference',
    'source_reference_kind', 'acquisition_at', 'acquisition_kind', 'method_ref',
    'identity', 'points', 'gaps', 'events', 'as_known', 'snapshot_compare',
    'revisions', 'track_record',
)
SOURCE_META_KEYS = (
    'source_reference', 'source_reference_kind', 'acquisition_at',
    'acquisition_kind', 'method_ref', 'identity',
)


def _args():
    return {
        'context': {
            'selected_market': 'JP',
            'horizon': '1m',
            'currency_basis': 'usd_unhedged',
            'return_basis': 'price',
        },
        'history_read': {
            'status': 'ready',
            'market_id': 'JP',
            'artifact_ref': 'intl_regime/JP_history.parquet',
            'read_at': '2026-10-08T12:00:00+00:00',
            'method_ref': 'intl_regime.classifier',
            'identity': {
                'market_id': 'JP',
                'unit': 'score',
                'return_basis': 'price',
                'universe': 'intl_regime.classifier_history',
                'method_ref': 'intl_regime.classifier',
            },
            'points': [
                {'observation_at': '2026-01-01T00:00:00+09:00', 'growth_score': 0.4375, 'inflation_score': -1.25},
                {'observation_at': '2026-01-02T00:00:00+09:00', 'growth_score': 17, 'inflation_score': 0.1875},
                {'observation_at': '2026-01-03T00:00:00.123456789+09:00', 'growth_score': 19, 'inflation_score': 23},
            ],
        },
        'turn_events': [
            {
                'market_id': 'JP', 'event_date': '2026-01', 'code': 'MA_TURN',
                'text_en': 'MA turn', 'text_zh': '均线转折',
                'evidence_ref': 'record.turn.events:0', 'source_reference': 'SECRET_EVENT_SRC',
            },
            {
                'market_id': 'KR', 'event_date': '2026-02-01', 'code': 'MACD_TURN',
                'text_en': 'Other market', 'text_zh': '其他市场',
                'evidence_ref': 'record.turn.events:9', 'source_reference': 'global_top_ten',
            },
        ],
        'track_record': {
            'market_id': 'JP', 'read_health': 'qualified', 'graded_count': 4, 'alert_count': 1,
            'sample_dates': ['2026-01-15', '2026-02-15'], 'precision': 0.5, 'hit_rate': 0.25,
            'lift': 1.5, 'false_alarms': 1, 'drawdowns': -0.1,
            'qualification_notes': 'forward_log independent read',
        },
        'capabilities': {
            'history_source': {'metadata': 'allowed', 'value': 'allowed'},
            'events': {'metadata': 'allowed', 'value': 'allowed'},
            'track_record': {'metadata': 'allowed', 'value': 'allowed'},
            'snapshot_compare': {
                'left_observation_at': '2026-01-01T00:00:00+09:00',
                'right_observation_at': '2026-01-02T00:00:00+09:00',
            },
        },
        'destinations': {
            'as_known': {
                'key': 'as_known', 'title_en': 'As-known vintages', 'title_zh': '当时已知',
                'destination': '/research/as-known',
            },
            'track_record': {
                'key': 'track_record', 'title_en': 'Track record', 'title_zh': '跟踪记录',
                'destination': '/research/track-record',
            },
            'revisions': {
                'key': 'revisions', 'title_en': 'Revisions', 'title_zh': '修订',
                'destination': None,
            },
        },
    }


def _call(mut=None):
    args = _args()
    if mut is not None:
        mut(args)
    return build_history_section(**args)


def _err(mut):
    with pytest.raises(ValueError) as caught:
        _call(mut)
    err = caught.value
    assert type(err) is ValueError
    assert str(err) == PUBLIC_ERROR
    assert err.args == (PUBLIC_ERROR,)
    assert err.__cause__ is None
    assert '.py' not in str(err)
    assert 'Traceback' not in str(err)
    return err


def test_unknown_sentinel_is_not_evaled():
    with pytest.raises(KeyError):
        SENTINELS['__import__("os")']


def test_closed_sentinel_mapping_rejects_nonfinite_and_objects():
    for python, path in (
        ("float('nan')", ['history_read', 'points', 0, 'growth_score']),
        ("float('inf')", ['history_read', 'points', 0, 'inflation_score']),
        ('object()', ['history_read', 'points']),
    ):
        args = _args()
        target = args
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = SENTINELS[python]
        with pytest.raises(ValueError) as caught:
            build_history_section(**args)
        assert str(caught.value) == PUBLIC_ERROR
        assert caught.value.__cause__ is None


def test_output_shape_mode_and_json_safety():
    result = _call()
    assert tuple(result) == OUTPUT_KEYS
    assert result['mode'] == 'recomputed'
    encoded = json.dumps(result, allow_nan=False)
    loaded = json.loads(encoded)
    assert loaded['mode'] == 'recomputed'
    assert result['as_known']['available'] is False
    assert result['revisions']['status'] == 'unavailable'
    assert result['revisions']['records'] == []


def test_no_mutation_or_shared_identity_with_inputs():
    args = _args()
    before = deepcopy(args)
    result = build_history_section(**args)
    assert args == before
    result['points'][0]['growth_score'] = 999
    result['identity']['method_ref'] = 'changed'
    result['events']['records'][0]['text_en'] = 'changed'
    result['track_record']['sample_dates'].clear()
    result['gaps'].append({'observation_at': 'x'})
    assert args == before
    assert result['points'][0] is not args['history_read']['points'][0]
    assert result['identity'] is not args['history_read']['identity']
    assert result['track_record']['sample_dates'] is not args['track_record']['sample_dates']


def test_no_io_during_projection(monkeypatch):
    def forbid_open(*_a, **_k):
        raise AssertionError('open')

    monkeypatch.setattr('builtins.open', forbid_open)
    result = _call()
    assert result['source_read_status'] == 'ready'


def test_direct_value_requires_metadata_and_value():
    allowed = _call()
    assert allowed['points'][0]['growth_score'] == 0.4375
    assert allowed['points'][0]['inflation_score'] == -1.25

    def deny_value(args):
        args['capabilities']['history_source']['value'] = 'denied'

    denied = _call(deny_value)
    assert denied['source_read_status'] == 'ready'
    assert denied['source_reference'] == 'intl_regime/JP_history.parquet'
    assert all(point['growth_score'] is None and point['inflation_score'] is None for point in denied['points'])
    assert denied['gaps'] == []
    assert denied['snapshot_compare']['reason'] == 'value_denied'
    assert '0.4375' not in json.dumps(denied)
    assert '-1.25' not in json.dumps(denied)

    def unknown_value(args):
        args['capabilities']['history_source']['value'] = 'unknown'

    unknown = _call(unknown_value)
    assert unknown['points'][0]['observation_at'] == '2026-01-01T00:00:00+09:00'
    assert unknown['points'][0]['growth_score'] is None
    assert unknown['gaps'] == []
    assert unknown['snapshot_compare']['reason'] == 'value_unknown'

    def deny_meta(args):
        args['capabilities']['history_source'] = {'metadata': 'denied', 'value': 'denied'}

    hidden = _call(deny_meta)
    encoded = json.dumps(hidden)
    assert hidden['source_read_status'] == 'denied'
    assert hidden['points'] == []
    assert hidden['gaps'] == []
    for key in SOURCE_META_KEYS:
        assert hidden[key] is None
    for token in (
        '0.4375', '-1.25', '19', 'intl_regime/JP_history.parquet', 'intl_regime.classifier',
        '2026-10-08T12:00:00+00:00', '2026-01-01T00:00:00+09:00', 'intl_regime.classifier_history',
    ):
        assert token not in encoded
    _err(lambda a: a['capabilities']['history_source'].update(metadata='denied', value='allowed'))


def test_denied_history_does_not_hide_independently_admitted_events_and_track():
    def mutate(args):
        args['capabilities']['history_source'] = {'metadata': 'denied', 'value': 'denied'}

    result = _call(mutate)
    assert result['events']['status'] == 'available'
    assert result['events']['records'][0]['code'] == 'MA_TURN'
    assert result['events']['records'][0]['history_kind'] == 'recomputed'
    assert result['track_record']['status'] == 'available'
    assert result['track_record']['hit_rate'] == 0.25
    assert result['snapshot_compare']['available_dates'] == []


def test_events_grant_does_not_hide_history():
    def mutate(args):
        args['capabilities']['events'] = {'metadata': 'denied', 'value': 'denied'}

    result = _call(mutate)
    assert result['events']['status'] == 'denied'
    assert result['events']['reason'] == 'metadata_denied'
    assert result['events']['completeness'] is None
    assert result['events']['records'] == []
    assert result['source_read_status'] == 'ready'
    assert result['points'][0]['growth_score'] == 0.4375


def test_event_wrong_market_exclusion_and_no_source_reference():
    result = _call()
    records = result['events']['records']
    assert [row['market_id'] for row in records] == ['JP']
    assert 'source_reference' not in records[0]
    encoded = json.dumps(result['events'])
    assert 'SECRET_EVENT_SRC' not in encoded
    assert 'MACD_TURN' not in encoded
    assert 'global_top_ten' not in encoded
    assert result['events']['completeness'] == 'selected_market_attached_only'
    assert result['events']['records'][0]['event_date'] == '2026-01'

    def only_other(args):
        args['turn_events'] = [args['turn_events'][1]]

    other = _call(only_other)
    assert other['events']['status'] == 'unavailable'
    assert other['events']['reason'] == 'wrong_market'
    assert other['events']['records'] == []
    assert 'MACD_TURN' not in json.dumps(other)


def test_event_value_unknown_and_empty_supply():
    unknown = _call(lambda a: a['capabilities']['events'].update(value='unknown'))
    assert unknown['events'] == {
        'status': 'unknown',
        'completeness': 'selected_market_attached_only',
        'reason': 'value_unknown',
        'records': [],
    }
    empty = _call(lambda a: a.update(turn_events=[]))
    assert empty['events']['reason'] == 'events_not_supplied'
    assert empty['events']['status'] == 'unavailable'


def test_event_order_preserved_and_month_not_coerced():
    def mutate(args):
        args['turn_events'] = [
            {**args['turn_events'][0], 'code': 'FIRST', 'event_date': '2026-01'},
            {**args['turn_events'][0], 'code': 'SECOND', 'event_date': '2026-03-01T00:00:00Z'},
            args['turn_events'][1],
        ]

    result = _call(mutate)
    assert [row['code'] for row in result['events']['records']] == ['FIRST', 'SECOND']
    assert result['events']['records'][0]['event_date'] == '2026-01'
    assert result['events']['records'][1]['event_date'] == '2026-03-01T00:00:00Z'


def test_missing_failed_empty_unsupported_are_distinct():
    def failed_bound(args):
        args['history_read'].update(status='failed', identity=None, points=[], method_ref=None)

    failed = _call(failed_bound)
    assert failed['source_read_status'] == 'failed'
    assert failed['source_reference'] == 'intl_regime/JP_history.parquet'
    assert failed['acquisition_at'] == '2026-10-08T12:00:00+00:00'
    assert failed['identity'] is None
    assert failed['points'] == []
    assert failed['snapshot_compare']['reason'] == 'source_failed'

    def missing_bound(args):
        args['history_read'].update(status='missing', identity=None, points=[], method_ref=None)

    missing = _call(missing_bound)
    assert missing['source_read_status'] == 'missing'
    assert missing['snapshot_compare']['reason'] == 'source_missing'

    def empty_bound(args):
        args['history_read']['status'] = 'empty'
        args['history_read']['points'] = []

    empty = _call(empty_bound)
    assert empty['source_read_status'] == 'empty'
    assert empty['identity']['unit'] == 'score'
    assert empty['points'] == []
    assert empty['gaps'] == []
    assert empty['snapshot_compare']['reason'] == 'source_empty'
    assert empty['snapshot_compare']['available_dates'] == []

    def unsupported_bound(args):
        args['history_read'].update(
            status='unsupported', identity=None, points=[],
            artifact_ref='bound/artifact', method_ref='bound-method',
            read_at='2026-10-08T12:00:00Z',
        )

    unsupported = _call(unsupported_bound)
    assert unsupported['source_read_status'] == 'unsupported'
    assert unsupported['source_reference'] == 'bound/artifact'
    assert unsupported['acquisition_at'] == '2026-10-08T12:00:00Z'
    assert unsupported['acquisition_kind'] == 'read_clock'
    assert unsupported['method_ref'] == 'bound-method'
    assert unsupported['snapshot_compare']['reason'] == 'source_unsupported'


def test_null_market_unsupported_does_not_borrow_clock_or_identity():
    def mutate(args):
        args['history_read'].update(
            status='unsupported', market_id=None, identity=None, points=[],
            artifact_ref='LEAK/artifact', method_ref='LEAK-METHOD',
            read_at='2026-10-08T12:00:00Z',
        )

    result = _call(mutate)
    assert result['source_read_status'] == 'unsupported'
    for key in SOURCE_META_KEYS:
        assert result[key] is None
    assert result['acquisition_kind'] is None
    assert 'LEAK' not in json.dumps(result)


@pytest.mark.parametrize('status', ['missing', 'failed', 'invalid', 'unsupported'])
def test_failed_unbound_reads_never_leak_source_identity(status):
    def mutate(args):
        args['history_read'].update(
            status=status, market_id=None, identity=None, points=[],
            artifact_ref='PRIVATE/artifact', method_ref='PRIVATE-METHOD',
            read_at='2026-10-08T12:00:00+00:00',
        )

    result = _call(mutate)
    assert result['source_read_status'] == status
    for key in SOURCE_META_KEYS:
        assert result[key] is None
    assert 'PRIVATE' not in json.dumps(result)


def test_wrong_market_and_unbound_strip_reconstruction():
    def wrong(args):
        args['history_read']['market_id'] = 'KR'
        args['history_read']['artifact_ref'] = 'intl_regime/KR_history.parquet'
        args['history_read']['identity']['market_id'] = 'KR'
        args['history_read']['points'] = [
            {'observation_at': '2026-01-01T00:00:00+09:00', 'growth_score': 9.75, 'inflation_score': 8.5},
        ]

    result = _call(wrong)
    assert result['source_read_status'] == 'wrong_market'
    for key in SOURCE_META_KEYS:
        assert result[key] is None
    assert result['points'] == []
    assert result['snapshot_compare']['reason'] == 'wrong_market'
    encoded = json.dumps(result)
    assert '9.75' not in encoded
    assert 'KR_history' not in encoded
    assert result['events']['status'] == 'available'

    unbound = _call(lambda a: a['context'].update(selected_market=None))
    assert unbound['source_read_status'] == 'unbound'
    assert unbound['selected_market'] is None
    assert unbound['acquisition_at'] is None
    assert unbound['events']['reason'] == 'market_not_selected'
    assert unbound['track_record']['reason'] == 'market_not_selected'
    assert unbound['snapshot_compare']['reason'] == 'market_not_selected'
    assert '0.4375' not in json.dumps(unbound)


def test_metadata_unknown_status_and_event_independence():
    result = _call(lambda a: a['capabilities']['history_source'].update(metadata='unknown', value='unknown'))
    assert result['source_read_status'] == 'unknown'
    assert result['snapshot_compare']['reason'] == 'disclosure_unknown'
    assert result['events']['status'] == 'available'


def test_nanosecond_timezone_month_precision_and_monotonicity():
    parsed = _parse_date('2026-01-03T00:00:00.123456789+09:00', False)
    assert parsed[1] == 'timestamp'
    assert parsed[2] == '+09:00'

    def months(args):
        args['history_read']['points'] = [
            {'observation_at': '2026-01', 'growth_score': 1, 'inflation_score': 2},
            {'observation_at': '2026-02', 'growth_score': 3, 'inflation_score': 4},
        ]
        args['capabilities']['snapshot_compare'] = {
            'left_observation_at': '2026-01', 'right_observation_at': '2026-02',
        }

    monthly = _call(months)
    assert monthly['points'][0]['observation_at'] == '2026-01'
    assert monthly['snapshot_compare']['eligible'] is True

    def nanos(args):
        args['history_read']['points'] = [
            {'observation_at': '2026-01-01T00:00:00.000000001Z', 'growth_score': 1, 'inflation_score': 2},
            {'observation_at': '2026-01-01T00:00:00.000000002Z', 'growth_score': 3, 'inflation_score': 4},
        ]
        args['capabilities']['snapshot_compare'] = {'left_observation_at': None, 'right_observation_at': None}

    nano = _call(nanos)
    assert nano['points'][0]['observation_at'] == '2026-01-01T00:00:00.000000001Z'

    _err(lambda a: a['history_read']['points'].__setitem__(1, {
        'observation_at': '2026-01-01T00:00:00.1Z', 'growth_score': 3, 'inflation_score': 4,
    }) or a['history_read']['points'].__setitem__(0, {
        'observation_at': '2026-01-01T00:00:00.10Z', 'growth_score': 1, 'inflation_score': 2,
    }))
    _err(lambda a: a['history_read']['points'][1].update(observation_at='2026-01'))
    _err(lambda a: a['history_read']['points'][1].update(observation_at='2026-01-02T00:00:00'))
    _err(lambda a: a['history_read']['points'][1].update(observation_at='2025-12-31T15:00:00Z'))
    _err(lambda a: a['history_read'].update(read_at='2026-10-08'))
    _err(lambda a: a['history_read'].update(read_at='2026-10-08T12:00:00'))
    _err(lambda a: a['history_read']['points'][0].update(observation_at='2026-13'))
    _err(lambda a: a['history_read']['points'][0].update(observation_at='2026-02-30'))


def test_compare_exact_string_not_canonical_zone():
    result = _call(lambda a: a['capabilities']['snapshot_compare'].update(
        right_observation_at='2026-01-02T00:00:00Z',
    ))
    assert result['snapshot_compare']['eligible'] is False
    assert result['snapshot_compare']['reason'] == 'observation_not_present'
    assert result['snapshot_compare']['left']['growth_score'] == 0.4375
    assert result['snapshot_compare']['right'] is None


def test_same_selected_dates_withhold_eligibility_keep_points():
    result = _call(lambda a: a['capabilities']['snapshot_compare'].update(
        left_observation_at='2026-01-02T00:00:00+09:00',
        right_observation_at='2026-01-02T00:00:00+09:00',
    ))
    assert result['snapshot_compare']['eligible'] is False
    assert result['snapshot_compare']['reason'] == 'same_observation'
    assert result['snapshot_compare']['left']['growth_score'] == 17
    assert result['snapshot_compare']['right']['inflation_score'] == 0.1875
    assert result['points'][1]['growth_score'] == 17


def test_comparability_withheld_while_separate_points_remain():
    def null_universe(args):
        args['history_read']['identity']['universe'] = None

    result = _call(null_universe)
    assert result['snapshot_compare']['eligible'] is False
    assert result['snapshot_compare']['reason'] == 'comparability_not_established'
    assert result['points'][0]['growth_score'] == 0.4375
    assert result['snapshot_compare']['left']['inflation_score'] == -1.25
    assert result['snapshot_compare']['right']['growth_score'] == 17

    def null_method(args):
        args['history_read']['method_ref'] = None
        args['history_read']['identity']['method_ref'] = None

    method = _call(null_method)
    assert method['snapshot_compare']['reason'] == 'comparability_not_established'
    assert method['method_ref'] is None
    assert method['points']


def test_null_gaps_and_absent_calendar_holes():
    def one_null(args):
        args['history_read']['points'][1]['growth_score'] = None

    gapped = _call(one_null)
    assert gapped['gaps'] == [{
        'observation_at': '2026-01-02T00:00:00+09:00',
        'field': 'growth_score',
        'reason': 'null_observation',
    }]
    assert gapped['snapshot_compare']['reason'] == 'gap_or_null_observation'
    assert gapped['snapshot_compare']['left']['growth_score'] == 0.4375
    assert gapped['points'][1]['inflation_score'] == 0.1875

    def both_null(args):
        args['history_read']['points'] = [
            {'observation_at': '2026-01-01T00:00:00Z', 'growth_score': None, 'inflation_score': None},
            {'observation_at': '2026-01-02T00:00:00Z', 'growth_score': 1, 'inflation_score': 2},
        ]
        args['capabilities']['snapshot_compare'] = {
            'left_observation_at': '2026-01-01T00:00:00Z',
            'right_observation_at': '2026-01-02T00:00:00Z',
        }

    dual = _call(both_null)
    assert [row['field'] for row in dual['gaps']] == ['growth_score', 'inflation_score']
    assert dual['snapshot_compare']['reason'] == 'gap_or_null_observation'

    def hole(args):
        args['history_read']['points'] = [
            {'observation_at': '2026-01-01T00:00:00Z', 'growth_score': 1, 'inflation_score': 2},
            {'observation_at': '2026-01-03T00:00:00Z', 'growth_score': 3, 'inflation_score': 4},
        ]
        args['capabilities']['snapshot_compare'] = {'left_observation_at': None, 'right_observation_at': None}

    holed = _call(hole)
    assert holed['gaps'] == []
    assert holed['snapshot_compare']['reason'] == 'not_requested'
    assert len(holed['points']) == 2


def test_value_denied_does_not_emit_source_nulls_as_gaps():
    def mutate(args):
        args['history_read']['points'][0]['growth_score'] = None
        args['capabilities']['history_source']['value'] = 'denied'

    result = _call(mutate)
    assert result['gaps'] == []
    assert all(point['growth_score'] is None for point in result['points'])


def test_track_record_health_zero_failed_not_empty_and_supplied_numbers():
    qualified_zero = _call(lambda a: a['track_record'].update(
        graded_count=0, alert_count=0, sample_dates=[], precision=None, hit_rate=None,
        lift=None, false_alarms=None, drawdowns=None,
    ))
    assert qualified_zero['track_record']['status'] == 'available'
    assert qualified_zero['track_record']['graded_count'] == 0
    assert qualified_zero['track_record']['status'] != 'empty'

    failed_zero = _call(lambda a: a['track_record'].update(
        read_health='failed', graded_count=0, alert_count=0, sample_dates=None,
        precision=None, hit_rate=None, lift=None, false_alarms=None, drawdowns=None,
        qualification_notes='forward_log read failed',
    ))
    assert failed_zero['track_record']['status'] == 'unavailable'
    assert failed_zero['track_record']['reason'] == 'read_health_failed'
    assert failed_zero['track_record']['graded_count'] is None
    assert 'forward_log read failed' not in json.dumps(failed_zero)

    retained = _call()
    assert retained['track_record']['hit_rate'] == 0.25
    assert retained['track_record']['drawdowns'] == -0.1
    assert 'success_rate' not in retained['track_record']
    assert 'calibrated' not in json.dumps(retained)

    denied = _call(lambda a: a['capabilities']['track_record'].update(value='denied'))
    assert denied['track_record']['status'] == 'denied'
    assert denied['track_record']['reason'] == 'value_denied'
    assert denied['track_record']['market_id'] == 'JP'
    assert denied['track_record']['sample_dates'] == ['2026-01-15', '2026-02-15']
    assert denied['track_record']['hit_rate'] is None
    assert denied['track_record']['qualification_notes'] is None

    wrong = _call(lambda a: a['track_record'].update(market_id='KR'))
    assert wrong['track_record']['reason'] == 'wrong_market'
    assert wrong['track_record']['hit_rate'] is None
    assert wrong['track_record']['market_id'] is None

    missing = _call(lambda a: a.update(track_record=None))
    assert missing['track_record']['reason'] == 'not_supplied'
    unsupported = _call(lambda a: a['track_record'].update(read_health='unsupported'))
    assert unsupported['track_record']['reason'] == 'read_health_unsupported'


def test_track_sample_dates_retain_order_and_month_precision():
    result = _call(lambda a: a['track_record'].update(sample_dates=['2026-03', '2026-01-15']))
    assert result['track_record']['sample_dates'] == ['2026-03', '2026-01-15']


def test_as_known_and_revisions_refuse_even_with_destinations_and_clocks():
    result = _call()
    assert result['as_known'] == {
        'available': False,
        'reason': 'immutable_vintages_not_supplied',
        'destination': '/research/as-known',
    }
    assert result['revisions'] == {
        'status': 'unavailable',
        'reason': 'no_linked_prior_versions',
        'records': [],
        'destination': None,
    }
    assert result['acquisition_kind'] == 'read_clock'
    assert 'first_known' not in json.dumps(result)
    _err(lambda a: a['capabilities'].__setitem__('as_known', {'metadata': 'allowed', 'value': 'allowed'}))


def test_safe_destination_reuse_and_empty_map():
    assert _destination(_args()['destinations']['as_known']) == 'as_known'
    fragment = _call(lambda a: a['destinations']['as_known'].update(destination='#as-known'))
    assert fragment['as_known']['destination'] == '#as-known'
    assert fragment['as_known']['available'] is False
    empty = _call(lambda a: a.update(destinations={}))
    assert empty['as_known']['destination'] is None
    assert empty['track_record']['destination'] is None
    assert empty['revisions']['destination'] is None
    _err(lambda a: a['destinations']['as_known'].update(destination='https://evil.test'))
    _err(lambda a: a['destinations']['as_known'].update(destination='//evil'))
    _err(lambda a: a['destinations'].__setitem__('spark', a['destinations']['as_known']))


def test_relative_artifact_identifier_and_macro_clocks():
    ok = _call(lambda a: a['history_read'].update(artifact_ref='intl_regime/JP_history.parquet'))
    assert ok['source_reference_kind'] == 'relative_reconstruction_artifact'
    for ref in (
        '/private/data', 'C:/private/data', 'https://example.test/x', 'a/../b', 'a/./b',
        'a//b', 'a\\b', 'a%20b', ' a', 'a ', 'a/', '../a', 'file:foo', 'intl_regime/日本.parquet',
    ):
        _err(lambda a, value=ref: a['history_read'].update(artifact_ref=value))
    zulu = _call(lambda a: a['history_read'].update(read_at='2026-10-08T12:00:00Z'))
    assert zulu['acquisition_at'] == '2026-10-08T12:00:00Z'


def test_int_float_bool_and_huge_finite_values():
    typed = _call(lambda a: (
        a['history_read']['points'][0].update(growth_score=0, inflation_score=0.0)
    ))
    assert type(typed['points'][0]['growth_score']) is int
    assert type(typed['points'][0]['inflation_score']) is float
    huge = _call(lambda a: a['history_read']['points'][0].update(growth_score=10 ** 400))
    assert huge['points'][0]['growth_score'] == 10 ** 400
    json.dumps(huge, allow_nan=False)
    _err(lambda a: a['history_read']['points'][0].update(growth_score=True))
    _err(lambda a: a['track_record'].update(alert_count=True))
    _err(lambda a: a['track_record'].update(graded_count=None))
    args = _args()
    args['history_read']['points'][0]['growth_score'] = float('-inf')
    with pytest.raises(ValueError) as caught:
        build_history_section(**args)
    assert str(caught.value) == PUBLIC_ERROR


def test_fixed_exception_has_no_path_or_inner_macro_text():
    for mut in (
        lambda a: a['context'].update(horizon=''),
        lambda a: a['context'].update(return_basis='total'),
        lambda a: a['history_read']['points'][0].update(observation_at='not-a-date'),
        lambda a: a['context'].update(horizon=a['context']),
        lambda a: a['history_read'].update(status='ready', points=[]),
        lambda a: a['turn_events'][0].__setitem__('rank', 1),
        lambda a: a['track_record'].__setitem__('success_rate', 0.9),
        lambda a: a['capabilities']['snapshot_compare'].update(right_observation_at=None),
    ):
        _err(mut)


def test_builtin_tree_rejects_dict_subclass():
    class Mapping(dict):
        pass

    args = _args()
    args['context'] = Mapping(args['context'])
    with pytest.raises(ValueError) as caught:
        build_history_section(**args)
    assert str(caught.value) == PUBLIC_ERROR


def test_history_kind_is_recomputed_never_first_known():
    result = _call()
    assert result['events']['records'][0]['history_kind'] == 'recomputed'
    assert result['mode'] == 'recomputed'
    assert result['as_known']['available'] is False
    assert result['snapshot_compare']['viewed_through'] == 'current_reconstruction'
