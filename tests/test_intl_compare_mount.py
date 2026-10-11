"""Compare composition consumes actual Overview owner projections."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest
import pandas as pd

from engine import intl_inputs
from engine.intl_performance_records import build_return_records
from engine.intl_workspace_overview import build_overview

from lib.intl_compare_mount import attach_compares


_spec = importlib.util.spec_from_file_location(
    'intl_compare_mount_fixture', Path(__file__).with_name('test_intl_inspector_view.py'))
_fixture = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fixture)


MARKETS = ['JP', 'GB']
HORIZONS = ['1m', '3m']
BASES = ['local', 'usd_unhedged']


_raw = build_return_records(
    pd.DataFrame({
        '^N225': [100 + index for index in range(30)],
        'USDJPY=X': [128 + index for index in range(30)],
        '^FTSE': [100 + index for index in range(30)],
        'GBPUSD=X': [1 + index / 100 for index in range(30)],
    }, index=pd.date_range('2025-12-10', periods=30)),
    market_ids=MARKETS, source_reference='synthetic:inspector-source')
_countries = intl_inputs.countries()
_roster = [
    {'market_id': market, 'name_en': _countries[market]['name'],
     'name_zh': _countries[market]['name_zh']} for market in MARKETS]


def project(*, horizon='1m', basis='usd_unhedged', **kwargs):
    decisions = kwargs.pop('decisions', True)
    edit = kwargs.pop('edit', None)
    qualifications = None
    if decisions:
        qualifications = []
        selected_leg = 'local' if basis == 'local' else 'usd'
        for record in _raw['records']:
            if record['horizon'] != horizon:
                continue
            for leg in ('local', 'usd', 'fx_contribution'):
                metric = record[leg]
                qualifications.append({
                    'binding': {
                        'source_reference': _raw['source_reference'],
                        'market_id': record['market_id'], 'index_id': record['index_id'],
                        'fx_id': record['fx_id'], 'horizon': horizon,
                        'currency_basis': basis, 'return_basis': 'price', 'leg': leg,
                        'value': metric['value'], 'unit': metric['unit'],
                        'window': deepcopy(metric['window'])},
                    'owner_ref': 'synthetic:source-owner',
                    'policy_ref': 'synthetic:policy', 'decision_ref': 'synthetic:decision',
                    'quality': 'qualified', 'reason': None,
                    'disclosure': {'metadata': 'allowed', 'value': 'allowed'}})
        if edit is not None:
            edit(qualifications)
    return build_overview(
        _raw, roster=_roster,
        context={'horizon': horizon, 'currency_basis': basis,
                 'return_basis': 'price',
                 'source_reference': _raw['source_reference']},
        qualifications=qualifications, **kwargs)


def workspace(*, edit=None):
    panels = []
    for horizon in HORIZONS:
        for basis in BASES:
            panels.append({
                'context_id': f'context-{horizon}-{basis}',
                'overview': project(horizon=horizon, basis=basis, edit=edit),
            })
    return {
        'config': {
            'markets': MARKETS, 'horizons': HORIZONS, 'bases': BASES,
            'default_horizon': '1m', 'default_basis': 'usd_unhedged',
            'source_reference': 'synthetic:inspector-source',
            'anchor_ids': ['intl-legacy-research'], 'library_group_ids': [],
        },
        'panels': panels,
    }


def deny(receipts):
    for receipt in receipts:
        if receipt['binding']['market_id'] == 'JP':
            receipt['disclosure']['metadata'] = 'denied'


def invalid(value):
    with pytest.raises(ValueError, match='invalid_compare_workspace$'):
        attach_compares(value)


def test_detached_workspace_preserves_every_existing_field():
    ws = workspace()
    before = deepcopy(ws)
    result = attach_compares(ws)
    assert ws == before
    assert result['config'] == before['config']
    assert result['panels'] == before['panels']
    assert [item['context_id'] for item in result['compares']] == [
        panel['context_id'] for panel in ws['panels']]
    assert all(
        set(item) == {'context_id', 'compare_catalogue'} for item in result['compares'])
    result['compares'][0]['compare_catalogue']['rows'][0]['name_en'] = 'edited'
    assert ws == before


def test_actual_owner_contexts_and_distinct_horizons_and_bases():
    result = attach_compares(workspace())
    assert len(result['compares']) == 4
    contexts = [item['compare_catalogue']['context'] for item in result['compares']]
    assert {(item['horizon'], item['currency_basis']) for item in contexts} == {
        (horizon, basis) for horizon in HORIZONS for basis in BASES}
    assert all(item['return_basis'] == 'price' for item in contexts)
    assert all(item['source_reference'] == 'synthetic:inspector-source' for item in contexts)


def test_denied_slot_keeps_canonical_position_without_identity():
    before = workspace(edit=deny)
    result = attach_compares(before)
    catalogue = result['compares'][0]['compare_catalogue']
    assert catalogue['slot_order'] == [0, 1]
    assert catalogue['rows'][0] == {'slot': 0, 'quality': 'denied', 'reason': 'metadata_denied'}
    assert catalogue['rows'][1]['market_id'] == 'GB'
    assert before == workspace(edit=deny)


def test_shuffled_rows_are_canonicalized():
    ws = workspace()
    for panel in ws['panels']:
        panel['overview']['rows'].reverse()
    result = attach_compares(ws)
    for compare in result['compares']:
        assert compare['compare_catalogue']['slot_order'] == [0, 1]
        assert [row['slot'] for row in compare['compare_catalogue']['rows']] == [0, 1]
        assert [row.get('market_id') for row in compare['compare_catalogue']['rows']] == MARKETS


@pytest.mark.parametrize('change', [
    lambda rows: rows.__setitem__(slice(None), rows[1:]),
    lambda rows: rows.append(deepcopy(rows[0])),
    lambda rows: rows[0].__setitem__('slot', 2),
    lambda rows: rows[1].__setitem__('slot', 0),
])
def test_missing_duplicate_and_out_of_range_slots_refuse(change):
    ws = workspace()
    change(ws['panels'][0]['overview']['rows'])
    invalid(ws)


def test_wrong_identity_for_config_position_refuses():
    ws = workspace()
    row = next(row for row in ws['panels'][0]['overview']['rows'] if row.get('market_id') == 'GB')
    row['market_id'] = 'TW'
    invalid(ws)


@pytest.mark.parametrize('field,value', [
    ('horizon', '12m'), ('currency_basis', 'total_return'), ('return_basis', 'total_return'),
    ('source_reference', 'synthetic:another-source'),
])
def test_context_binding_mismatch_refuses(field, value):
    ws = workspace()
    ws['panels'][0]['overview']['context'][field] = value
    invalid(ws)


def test_duplicate_context_id_or_binding_tuple_refuses():
    duplicate_id = workspace()
    duplicate_id['panels'][1]['context_id'] = duplicate_id['panels'][0]['context_id']
    invalid(duplicate_id)
    duplicate_tuple = workspace()
    duplicate_tuple['panels'][1]['overview']['context'] = deepcopy(
        duplicate_tuple['panels'][0]['overview']['context'])
    invalid(duplicate_tuple)


def test_none_passthrough_and_malformed_config_refuse():
    assert attach_compares(None) is None
    ws = workspace()
    ws['config']['markets'] = ['JP', 'GB', 'INVENTED']
    invalid(ws)
    malformed = workspace()
    malformed['config'].pop('anchor_ids')
    invalid(malformed)


def test_preserves_existing_library_inspector_and_workspace_metadata():
    ws = workspace()
    ws.update(library={'tools': ['retained']}, inspectors=[{'context': 'retained'}],
              publication={'opaque': ['retained']})
    before = deepcopy(ws)
    result = attach_compares(ws)
    assert {k: result[k] for k in before} == before
    result['library']['tools'].append('new')
    assert ws == before


def test_composition_does_not_reload_global_roster_or_perform_input_io(monkeypatch):
    ws = workspace()
    def unexpected():
        raise AssertionError('composition must use supplied workspace roster')
    monkeypatch.setattr(intl_inputs, 'countries', unexpected)
    result = attach_compares(ws)
    assert len(result['compares']) == 4


@pytest.mark.parametrize('row', [None, [], 'invalid'])
def test_malformed_row_returns_documented_composition_refusal(row):
    ws = workspace(); ws['panels'][0]['overview']['rows'][0] = row
    invalid(ws)
