"""Synthetic decisions exercise the actual return owner and Overview consumer."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

from engine.intl_performance_records import build_return_records
from lib.intl_compare_view import build_compare_view

spec = importlib.util.spec_from_file_location(
    'compare_owner_fixture', Path(__file__).with_name('test_intl_inspector_view.py'))
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
supplied = fixture.supplied


def compare(view, slots=None):
    return build_compare_view(view, selected_slots=[0, 1] if slots is None else slots)


def test_actual_owner_endpoint_table_preserves_user_order_values_and_identity(supplied):
    view = supplied[0](); before = deepcopy(view)
    result = compare(view, [1, 0])
    assert result['status'] == 'comparable' and result['reason'] is None
    assert result['order_slots'] == [1, 0]
    assert [row['slot'] for row in result['rows']] == [1, 0]
    assert result['rows'][1]['index_label'] == 'Nikkei 225'
    for output, original in zip(result['rows'], reversed(view['rows'])):
        for leg in ('local', 'usd', 'fx_contribution'):
            assert output[leg] == original[leg]
    assert set(result) == {'context', 'status', 'reason', 'selected_count', 'rows',
                           'common_window', 'order_slots', 'chart', 'benchmark'}
    assert result['chart'] == {'status': 'unavailable', 'reason': 'series_qualification_not_supplied'}
    assert result['benchmark'] == {'status': 'unavailable', 'reason': 'not_supplied'}
    result['rows'][0]['usd']['window']['end'] = 'changed'
    result['context']['horizon'] = 'changed'
    assert view == before
    json.dumps(compare(view), allow_nan=False)


@pytest.mark.parametrize('slots', [[], [0], [1]])
def test_incomplete_selection_is_explicit_and_does_not_invent_a_pair(supplied, slots):
    result = compare(supplied[0](), slots)
    assert result['status'] == 'incomplete_selection'
    assert result['selected_count'] == len(slots)
    assert result['order_slots'] == [] and result['common_window'] is None


@pytest.mark.parametrize('key,value', [('start', '2025-12-19T00:00:00'),
                                     ('end', '2026-01-09T00:00:00'),
                                     ('calendar_policy', 'observed_local_prices')])
def test_unequal_windows_preserve_individual_returns_but_withhold_shared_order(supplied, key, value):
    raw = deepcopy(supplied[1])
    for row in raw['records']:
        if row['market_id'] == 'JP' and row['horizon'] == '1m':
            row['usd']['window'][key] = value
    view = supplied[0](data=raw); result = compare(view)
    assert result['status'] == 'withheld' and result['reason'] == 'unequal_windows'
    assert result['order_slots'] == [] and result['common_window'] is None
    assert result['rows'][0]['usd'] == view['rows'][0]['usd']
    assert result['selected_count'] == 2


def test_different_contributor_dates_do_not_change_accepted_calculation_window(supplied):
    raw = deepcopy(supplied[1])
    for row in raw['records']:
        if row['market_id'] == 'JP' and row['horizon'] == '1m':
            row['usd']['window']['endpoint_observations']['price_start'] = '2025-12-17T00:00:00'
    view = supplied[0](data=raw)
    assert compare(view)['status'] == 'comparable'
    assert compare(view)['rows'][0]['usd']['window'] == view['rows'][0]['usd']['window']


def test_actual_local_only_returns_work_without_fx_or_chart_rights(supplied):
    frame = supplied[2].drop(columns=['USDJPY=X', 'GBPUSD=X'])
    raw = build_return_records(frame, market_ids=['JP', 'GB'], source_reference='synthetic:local')
    view = supplied[0](basis='local', data=raw); result = compare(view)
    assert result['status'] == 'comparable'
    assert all(row['local']['value'] is not None and row['usd']['value'] is None for row in result['rows'])
    assert compare(supplied[0](data=raw))['reason'] == 'selection_unqualified'


@pytest.mark.parametrize('quality', ['stale', 'missing', 'denied', 'failed', 'unsupported', 'unknown'])
def test_unqualified_selection_is_retained_never_silently_removed(supplied, quality):
    def edit(receipts):
        for r in receipts:
            if r['binding']['market_id'] == 'JP':
                if quality == 'denied': r['disclosure']['value'] = 'denied'
                else: r.update(quality=quality, reason='private:must-not-leak')
    result = compare(supplied[0](edit=edit))
    assert result['reason'] == 'selection_unqualified'
    assert result['selected_count'] == 2 and result['order_slots'] == []
    assert result['rows'][0]['usd']['value'] is None
    assert 'private:must-not-leak' not in json.dumps(result)


def test_denied_metadata_remains_slot_only(supplied):
    def edit(receipts):
        for r in receipts:
            if r['binding']['market_id'] == 'JP': r['disclosure']['metadata'] = 'denied'
    result = compare(supplied[0](edit=edit))
    assert result['rows'][0] == {'slot': 0, 'quality': 'denied', 'reason': 'metadata_denied'}
    assert 'JP' not in json.dumps(result) and 'Nikkei' not in json.dumps(result)
    assert result['reason'] == 'selection_unqualified'


def test_no_receipts_stays_unknown_and_does_not_borrow_numbers(supplied):
    result = compare(supplied[0](decisions=False))
    assert result['reason'] == 'selection_unqualified'
    assert result['context']['source_reference'] is None
    assert all(row['usd']['value'] is None and row['usd']['quality'] == 'unknown' for row in result['rows'])


@pytest.mark.parametrize('reason', ['value_denied', 'value_unknown', 'numerical_unavailable'])
def test_disclosed_owner_reason_vocabulary_is_preserved(supplied, reason):
    data = deepcopy(supplied[1])
    if reason == 'numerical_unavailable':
        for row in data['records']:
            if row['market_id'] == 'JP' and row['horizon'] == '1m':
                row['usd'].update(value=None, numerical_status='unavailable',
                                  reason='synthetic:no-value', window=None)
    def edit(receipts):
        for receipt in receipts:
            if receipt['binding']['market_id'] == 'JP' and receipt['binding']['leg'] == 'usd':
                if reason != 'numerical_unavailable':
                    receipt['disclosure']['value'] = reason.removeprefix('value_')
    view = supplied[0](data=data, edit=edit)
    assert view['rows'][0]['usd']['reason'] == reason
    result = compare(view)
    assert result['rows'][0]['usd']['reason'] == reason
    assert result['rows'][0]['usd']['value'] is None
    assert result['reason'] == 'selection_unqualified' and result['order_slots'] == []


@pytest.mark.parametrize('values,order', [([0, 0], [1, 0]), ([-8, -9], [0, 1]),
    ([1.000000000001, 1.000000000002], [1, 0]), ([10**350, 10**350+1], [1, 0])])
def test_zero_negative_ties_near_ties_and_large_integers_are_not_rounded(supplied, values, order):
    view = supplied[0]()
    for row, value in zip(view['rows'], values):
        row['usd']['value'] = row['metric']['value'] = value
    result = compare(view)
    assert result['order_slots'] == order
    assert [row['usd']['value'] for row in result['rows']] == values
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize('count', [3, 4])
def test_three_four_selected_slots_remain_in_requested_order(supplied, count):
    view = supplied[0]()
    # Extra synthetic consumer rows copy an actual owner interval; not new live markets.
    for slot in range(2, count):
        row = deepcopy(view['rows'][0]); row.update(slot=slot, market_id='TEST'+str(slot))
        view['rows'].append(row)
    view['configured_count'] = count
    slots = list(reversed(range(count)))
    result = compare(view, slots)
    assert result['status'] == 'comparable' and result['selected_count'] == count
    assert [row['slot'] for row in result['rows']] == slots
    assert set(result['order_slots']) == set(slots)


@pytest.mark.parametrize('slots', [[True], [0, 0], [0, 1, 2, 3, 4], [-1], [3], [0.0], ('0',), None])
def test_invalid_slot_requests_refuse(supplied, slots):
    with pytest.raises(ValueError, match='^invalid_compare_input$'):
        build_compare_view(supplied[0](), selected_slots=slots)


@pytest.mark.parametrize('value', [float('nan'), float('inf'), True, '12'])
def test_invalid_metric_types_refuse(supplied, value):
    view = supplied[0](); view['rows'][0]['metric']['value'] = value
    with pytest.raises(ValueError, match='^invalid_compare_input$'): compare(view)


def test_window_chronology_uses_existing_owner_validation(supplied):
    view = supplied[0](); view['rows'][0]['usd']['window']['start'] = '2050-01-01T00:00:00'
    view['rows'][0]['metric'] = deepcopy(view['rows'][0]['usd'])
    with pytest.raises(ValueError, match='^invalid_compare_input$'): compare(view)


def test_proxy_containers_are_rejected_without_invoking_methods(supplied):
    class Hostile(dict):
        def items(self): raise AssertionError('user hook executed')
        def __getitem__(self, key): raise AssertionError('user hook executed')
    with pytest.raises(ValueError, match='^invalid_compare_input$'): compare(Hostile(supplied[0]()))


def catalogue(view):
    from lib import intl_compare_view
    return intl_compare_view.build_compare_catalogue(view)


def test_catalogue_is_one_detached_public_row_per_configured_slot(supplied):
    view = supplied[0](); before = deepcopy(view)
    result = catalogue(view)
    assert set(result) == {'schema', 'context', 'slot_order', 'rows', 'cohorts', 'chart', 'benchmark'}
    assert result['schema'] == 'intl-compare-catalogue.v1'
    assert result['slot_order'] == [0, 1]
    assert [row['slot'] for row in result['rows']] == [0, 1]
    assert [row['cohort_id'] for row in result['rows']] == ['c0', 'c0']
    expected = compare(view)
    assert result['cohorts'] == [{'id': 'c0', 'window': expected['common_window'],
                                  'order_slots': expected['order_slots']}]
    assert result['chart'] == expected['chart'] and result['benchmark'] == expected['benchmark']
    for row, selected in zip(result['rows'], expected['rows']):
        assert {k: v for k, v in row.items() if k != 'cohort_id'} == selected
    result['context']['source_reference'] = 'changed'
    result['rows'][0]['usd']['window']['end'] = 'changed'
    result['cohorts'][0]['window']['start'] = 'changed'
    assert view == before
    json.dumps(catalogue(view), allow_nan=False)


def test_catalogue_every_ordered_zero_to_four_selection_matches_actual_table(supplied):
    from itertools import permutations
    view = supplied[0]()
    # Four extra synthetic consumer rows preserve the actual owner's schema.
    for slot in (2, 3):
        row = deepcopy(view['rows'][0]); row.update(slot=slot, market_id='TEST'+str(slot))
        row['usd']['window']['start'] = '2025-12-19T00:00:00'
        row['metric'] = deepcopy(row['usd'])
        view['rows'].append(row)
    view['rows'].append({'slot': 4, 'quality': 'denied', 'reason': 'metadata_denied'})
    unknown = deepcopy(supplied[0](decisions=False)['rows'][0])
    unknown.update(slot=5, market_id='UNKNOWN')
    view['rows'].append(unknown); view['configured_count'] = 6
    result = catalogue(view)
    rows = {row['slot']: row for row in result['rows']}
    groups = {group['id']: group for group in result['cohorts']}
    assert [group['id'] for group in result['cohorts']] == ['c0', 'c1']
    assert rows[4] == view['rows'][4] and 'cohort_id' not in rows[4]
    assert rows[5]['cohort_id'] is None
    checked = 0
    for size in range(5):
        for selected in permutations(range(6), size):
            table = compare(view, list(selected))
            cohort_ids = [rows[slot].get('cohort_id') for slot in selected]
            if size < 2:
                status, reason, order, window = 'incomplete_selection', 'insufficient_selection', [], None
            elif None in cohort_ids:
                status, reason, order, window = 'withheld', 'selection_unqualified', [], None
            elif len(set(cohort_ids)) != 1:
                status, reason, order, window = 'withheld', 'unequal_windows', [], None
            else:
                group = groups[cohort_ids[0]]
                status, reason, window = 'comparable', None, group['window']
                order = [slot for slot in group['order_slots'] if slot in selected]
            assert (status, reason, order, window) == (table['status'], table['reason'],
                table['order_slots'], table['common_window']), selected
            checked += 1
    assert checked == 517


def test_catalogue_slot_mapping_is_canonical_even_if_rows_are_reordered(supplied):
    view = supplied[0](); expected = catalogue(view)
    view['rows'].reverse()
    assert catalogue(view) == expected


@pytest.mark.parametrize('slots', [[1, 2], [0, 9], [0, 0], [True, 1]])
def test_catalogue_refuses_noncanonical_slots_before_mapping_to_config(supplied, slots):
    view = supplied[0]()
    for row, slot in zip(view['rows'], slots): row['slot'] = slot
    with pytest.raises(ValueError, match='^invalid_compare_input$'): catalogue(view)


@pytest.mark.parametrize('values,order', [([0, 0], [1, 0]), ([-8, -9], [0, 1]),
    ([1.000000000001, 1.000000000002], [1, 0]), ([10**350, 10**350+1], [1, 0])])
def test_catalogue_keeps_unrounded_server_order(supplied, values, order):
    view = supplied[0]()
    for row, value in zip(view['rows'], values): row['usd']['value'] = row['metric']['value'] = value
    result = catalogue(view)
    assert result['cohorts'][0]['order_slots'] == order
    assert [row['usd']['value'] for row in result['rows']] == values


def test_catalogue_local_only_remains_useful_without_chart_grant(supplied):
    frame = supplied[2].drop(columns=['USDJPY=X', 'GBPUSD=X'])
    raw = build_return_records(frame, market_ids=['JP', 'GB'], source_reference='synthetic:local')
    result = catalogue(supplied[0](basis='local', data=raw))
    assert len(result['cohorts']) == 1
    assert all(row['local']['value'] is not None and row['usd']['value'] is None for row in result['rows'])
    assert result['chart']['status'] == 'unavailable'
    assert catalogue(supplied[0](data=raw))['cohorts'] == []


def test_catalogue_missing_source_does_not_create_qualified_cohorts(supplied):
    view = supplied[0](); view['context']['source_reference'] = None
    result = catalogue(view)
    assert result['cohorts'] == []
    assert all(row['cohort_id'] is None for row in result['rows'])


def test_catalogue_denied_and_unknown_metadata_never_gain_identity(supplied):
    def deny(receipts):
        for receipt in receipts:
            if receipt['binding']['market_id'] == 'JP': receipt['disclosure']['metadata'] = 'denied'
    result = catalogue(supplied[0](edit=deny))
    assert result['rows'][0] == {'slot': 0, 'quality': 'denied', 'reason': 'metadata_denied'}
    assert result['cohorts'][0]['order_slots'] == [1]
    assert 'JP' not in json.dumps(result) and 'Nikkei' not in json.dumps(result)
    unknown = catalogue(supplied[0](decisions=False))
    assert unknown['cohorts'] == []
    assert all(row['local']['value'] is None for row in unknown['rows'])


def test_catalogue_payload_is_linear_not_precomputed_selections(supplied):
    view = supplied[0]()
    for slot in range(2, 150):
        row = deepcopy(view['rows'][slot % 2]); row.update(slot=slot, market_id='TEST'+str(slot))
        view['rows'].append(row)
    view['configured_count'] = 150
    result = catalogue(view)
    assert len(result['rows']) == len(result['slot_order']) == 150
    assert sum(len(group['order_slots']) for group in result['cohorts']) == 150
    assert len(result['cohorts']) == 1
