"""Independent currency-channel counterexamples. Do not import author tests."""
import copy
import json
import math
import traceback
from pathlib import Path

import pytest

from lib.intl_workspace_risk_currency import build_currency_channel

FIXTURE = Path(__file__).parent / 'fixtures/intl_workspace/risk_currency_overview.json'
SECRET = 'SECRET_LEAK_TOKEN_9f3c'
OUTPUT_KEYS = {
    'slot', 'market', 'context', 'local_return', 'usd_return',
    'fx_return_usd_per_local', 'fx_contribution_pp', 'arithmetic_quality',
    'reason', 'endpoint_policy', 'input_evidence_refs',
}
CONTEXT_KEYS = {'horizon', 'currency_basis', 'return_basis', 'source_reference'}


def load_overview():
    return json.loads(FIXTURE.read_text())


def kr_overview(local=-1.8, usd=-2.5856, contribution=-0.7856):
    obj = load_overview()
    obj['focus_ids'] = ['GB']
    row = obj['rows'][0]
    row.update(
        market_id='KR', name_en='South Korea', name_zh='韩国',
        index_id='^KS11', index_label='KOSPI',
    )
    for leg, value in (('local', local), ('usd', usd), ('fx_contribution', contribution)):
        row[leg]['value'] = value
    row['metric'] = copy.deepcopy(row['usd'])
    return obj


def call(obj, slot=0):
    return build_currency_channel(obj, selected_slot=slot)


def contract_fx(local, usd):
    return ((1 + usd / 100) / (1 + local / 100) - 1) * 100


def assert_no_nonfinite(obj, path='out'):
    if isinstance(obj, float):
        assert math.isfinite(obj), path
    elif isinstance(obj, dict):
        for key, value in obj.items():
            assert_no_nonfinite(value, path + '.' + key)
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            assert_no_nonfinite(value, f'{path}[{index}]')


def test_gb_slot_uses_multiplicative_fx_not_percentage_point_gap():
    obj = load_overview()
    before = copy.deepcopy(obj)
    out = call(obj, 1)
    local = obj['rows'][1]['local']['value']
    usd = obj['rows'][1]['usd']['value']
    contribution = obj['rows'][1]['fx_contribution']['value']
    gap = usd - local
    fx = out['fx_return_usd_per_local']['value']
    assert out['slot'] == 1
    assert out['market']['market_id'] == 'GB'
    assert out['market']['index_id'] == '^FTSE'
    assert 'JP' not in json.dumps(out['market'])
    assert 'Nikkei' not in json.dumps(out['market'])
    assert out['arithmetic_quality'] == 'qualified'
    assert out['fx_contribution_pp']['value'] == contribution
    assert out['fx_contribution_pp']['unit'] == 'percentage_points'
    assert out['fx_return_usd_per_local']['unit'] == 'percent'
    assert out['fx_return_usd_per_local']['derivation'] == 'derived_from_disclosed_returns'
    assert fx == pytest.approx(contract_fx(local, usd), rel=1e-12, abs=1e-12)
    assert fx != pytest.approx(contribution)
    assert fx != pytest.approx(gap)
    assert contribution == pytest.approx(gap)
    assert obj == before


def test_contribution_equal_to_raw_fx_is_mismatch_and_is_not_repaired():
    obj = kr_overview(local=10, usd=21, contribution=10)
    out = call(obj)
    assert out['fx_return_usd_per_local']['value'] == pytest.approx(10)
    assert out['fx_contribution_pp']['value'] == 10
    assert out['reason'] == 'contribution_mismatch'
    assert out['arithmetic_quality'] == 'partial'
    assert out['local_return']['value'] == 10
    assert out['usd_return']['value'] == 21
    assert out['fx_contribution_pp']['value'] != pytest.approx(11)


def test_usd_complete_loss_is_raw_fx_minus_100_for_nonzero_local():
    obj = kr_overview(local=25, usd=-100, contribution=-125)
    out = call(obj)
    assert out['fx_return_usd_per_local']['value'] == pytest.approx(-100)
    assert out['fx_contribution_pp']['value'] == -125
    assert out['arithmetic_quality'] == 'qualified'
    assert out['local_return']['value'] == 25


def test_local_minus_100_is_invalid_denominator_even_with_usd_minus_100():
    obj = kr_overview(local=-100, usd=-100, contribution=0)
    out = call(obj)
    assert out['fx_return_usd_per_local']['value'] is None
    assert out['endpoint_policy'] is None
    assert out['input_evidence_refs'] == []
    assert out['local_return']['value'] == -100
    assert out['usd_return']['value'] == -100
    assert out['arithmetic_quality'] == 'partial'


def test_redacted_other_slot_does_not_borrow_selected_neighbor():
    obj = kr_overview()
    obj['rows'][1] = {'slot': 1, 'quality': 'denied', 'reason': 'metadata_denied'}
    obj['focus_ids'] = ['KR']
    out = call(obj, 1)
    blob = json.dumps(out, ensure_ascii=False)
    assert out['market'] is None
    assert out['context']['source_reference'] is None
    assert out['arithmetic_quality'] == 'unavailable'
    assert out['slot'] == 1
    for token in ('KR', 'Korea', '韩国', 'KOSPI', 'KS11', 'synthetic',
                  'GB', 'United Kingdom', 'FTSE', 'JP', 'Nikkei'):
        assert token not in blob
    assert all(
        out[key]['value'] is None
        for key in ('local_return', 'usd_return', 'fx_return_usd_per_local', 'fx_contribution_pp')
    )


def test_unknown_selected_slot_keeps_own_identity_without_other_row_returns():
    obj = load_overview()
    obj['rows'][0] = {
        'slot': 0,
        'market_id': 'JP',
        'name_en': 'Japan',
        'name_zh': '日本',
        'quality': 'unknown',
        'reason': 'qualification_unknown',
        'metric': {
            'value': None, 'unit': 'percent', 'quality': 'unknown',
            'reason': 'qualification_unknown',
        },
    }
    out = call(obj, 0)
    blob = json.dumps(out, ensure_ascii=False)
    assert out['market']['market_id'] == 'JP'
    assert out['market']['name_en'] == 'Japan'
    assert 'index_id' not in out['market']
    assert out['context']['source_reference'] is None
    assert out['usd_return']['value'] is None
    assert out['local_return']['value'] is None
    assert out['fx_return_usd_per_local']['value'] is None
    assert 'GB' not in blob
    assert 'United Kingdom' not in blob
    assert 'FTSE' not in blob
    assert 'synthetic' not in blob
    assert 42.66975308641974 not in (
        out['usd_return']['value'], out['local_return']['value'],
        out['fx_contribution_pp']['value'],
    )


def test_private_metric_reason_does_not_cross_compare_boundary():
    obj = kr_overview()
    obj['rows'][0]['local'].update(
        value=None, quality='unknown', reason='raw_internal_secret', window=None,
    )
    obj['rows'][0]['metric'] = copy.deepcopy(obj['rows'][0]['usd'])
    out = call(obj)
    blob = json.dumps(out)
    assert 'raw_internal_secret' not in blob
    assert out['local_return']['quality'] == 'unknown'
    assert out['usd_return']['quality'] == 'qualified'
    assert out['usd_return']['value'] == pytest.approx(-2.5856)
    assert out['fx_return_usd_per_local']['value'] is None
    assert out['endpoint_policy'] is None


def test_price_start_mismatch_withholds_even_when_calendar_window_matches():
    obj = kr_overview()
    obj['rows'][0]['local']['window']['endpoint_observations']['price_start'] = '2025-12-17T00:00:00'
    out = call(obj)
    assert obj['rows'][0]['local']['window']['start'] == obj['rows'][0]['usd']['window']['start']
    assert obj['rows'][0]['local']['window']['end'] == obj['rows'][0]['usd']['window']['end']
    assert obj['rows'][0]['local']['window']['calendar_policy'] == obj['rows'][0]['usd']['window']['calendar_policy']
    assert out['fx_return_usd_per_local']['value'] is None
    assert out['endpoint_policy'] is None
    assert out['local_return']['value'] == pytest.approx(-1.8)
    assert out['usd_return']['value'] == pytest.approx(-2.5856)
    assert out['arithmetic_quality'] == 'partial'


def test_fx_observation_mismatch_keeps_usd_leg_geometry_on_derived_fx():
    obj = kr_overview()
    obj['rows'][0]['local']['window']['endpoint_observations']['fx_start'] = '2025-12-17T00:00:00'
    out = call(obj)
    fx_window = out['fx_return_usd_per_local']['window']
    assert out['fx_return_usd_per_local']['quality'] == 'qualified'
    assert fx_window['endpoint_observations']['fx_start'] == '2025-12-18T00:00:00'
    assert fx_window['endpoint_observations']['price_start'] == '2025-12-18T00:00:00'
    assert out['local_return']['window']['endpoint_observations']['fx_start'] == '2025-12-17T00:00:00'
    assert out['endpoint_policy']['endpoint_observations']['fx_start'] == '2025-12-18T00:00:00'


def test_stale_contribution_allows_raw_fx_denied_contribution_does_not():
    stale = kr_overview()
    stale['rows'][0]['fx_contribution'].update(
        value=None, quality='stale', reason='quality_stale', window=None,
    )
    stale['rows'][0]['metric'] = copy.deepcopy(stale['rows'][0]['usd'])
    stale_out = call(stale)
    assert stale_out['fx_return_usd_per_local']['value'] == pytest.approx(-0.8)
    assert stale_out['fx_contribution_pp']['quality'] == 'stale'
    assert stale_out['arithmetic_quality'] == 'partial'

    denied = kr_overview()
    denied['rows'][0]['fx_contribution'].update(
        value=None, quality='denied', reason='value_denied', window=None,
    )
    denied['rows'][0]['metric'] = copy.deepcopy(denied['rows'][0]['usd'])
    denied_out = call(denied)
    assert denied_out['local_return']['quality'] == 'qualified'
    assert denied_out['usd_return']['quality'] == 'qualified'
    assert denied_out['fx_return_usd_per_local']['value'] is None
    assert denied_out['input_evidence_refs'] == []
    assert denied_out['endpoint_policy'] is None
    assert denied_out['fx_contribution_pp']['quality'] == 'denied'


def test_output_windows_are_detached_from_input_and_each_other():
    obj = kr_overview()
    shared = obj['rows'][0]['local']
    obj['rows'][0]['usd'] = shared
    obj['rows'][0]['metric'] = shared
    before = copy.deepcopy(obj)
    out = call(obj)
    assert out['local_return'] is not obj['rows'][0]['local']
    assert out['usd_return'] is not obj['rows'][0]['usd']
    assert out['local_return'] is not out['usd_return']
    assert out['local_return']['window'] is not out['usd_return']['window']
    assert out['endpoint_policy'] is not out['fx_return_usd_per_local']['window']
    assert out['endpoint_policy'] is not out['usd_return']['window']
    out['local_return']['value'] = 999
    out['endpoint_policy']['start'] = 'changed'
    out['market']['name_en'] = 'changed'
    out['fx_return_usd_per_local']['window']['end'] = 'changed'
    obj['rows'][0]['local']['value'] = 12345
    obj['context']['source_reference'] = 'invented-nonce'
    assert before['rows'][0]['local']['value'] == -1.8
    assert out['usd_return']['value'] == -1.8
    assert out['fx_return_usd_per_local']['window']['start'] == '2025-12-18T00:00:00'
    assert out['context']['source_reference'] == 'synthetic:inspector-source'


def test_owner_minus_zero_survives_on_independent_legs():
    obj = kr_overview(local=-0.0, usd=-0.0, contribution=-0.0)
    out = call(obj)
    assert math.copysign(1, out['local_return']['value']) < 0
    assert math.copysign(1, out['usd_return']['value']) < 0
    assert math.copysign(1, out['fx_contribution_pp']['value']) < 0
    assert out['fx_return_usd_per_local']['value'] == pytest.approx(0)


def test_overflowing_integer_withholds_derived_and_preserves_owner_int():
    huge = 10 ** 400
    obj = kr_overview(local=huge, usd=1, contribution=0)
    out = call(obj)
    assert out['fx_return_usd_per_local']['value'] is None
    assert out['local_return']['value'] == huge
    assert out['usd_return']['value'] == 1
    assert out['fx_contribution_pp']['value'] == 0
    assert out['endpoint_policy'] is None
    assert_no_nonfinite(out)


def test_huge_owner_contribution_is_not_repaired_when_pair_is_valid():
    huge = 10 ** 400
    obj = kr_overview(local=1, usd=2, contribution=huge)
    out = call(obj)
    assert out['fx_contribution_pp']['value'] == huge
    assert out['fx_return_usd_per_local']['value'] == pytest.approx(contract_fx(1, 2))
    assert out['arithmetic_quality'] == 'partial'
    assert out['reason'] == 'contribution_mismatch'


def test_exact_timestamp_string_mismatch_is_not_chronology_coerced():
    obj = kr_overview()
    for leg in ('local', 'usd', 'fx_contribution', 'metric'):
        window = obj['rows'][0][leg]['window']
        window['start'] = '2025-12-18T00:00:00+00:00'
        window['end'] = '2026-01-08T00:00:00+00:00'
        for key, stamp in list(window['endpoint_observations'].items()):
            window['endpoint_observations'][key] = stamp + '+00:00'
    obj['rows'][0]['local']['window']['start'] = '2025-12-18T00:00:00Z'
    out = call(obj)
    assert out['fx_return_usd_per_local']['value'] is None
    assert out['endpoint_policy'] is None
    assert out['local_return']['value'] == pytest.approx(-1.8)
    assert out['usd_return']['value'] == pytest.approx(-2.5856)


def test_price_contributor_after_window_end_is_invalid_input():
    obj = kr_overview()
    obj['rows'][0]['local']['window']['endpoint_observations']['price_end'] = '2026-01-09T00:00:00'
    with pytest.raises(ValueError, match='^invalid_currency_channel_input$'):
        call(obj)


def test_malformed_and_hostile_inputs_use_fixed_message_without_raw_leak():
    cases = [
        None,
        [],
        'overview',
        {},
        load_overview() | {'extra': SECRET},
    ]
    for payload in cases:
        with pytest.raises(ValueError, match='^invalid_currency_channel_input$') as caught:
            call(payload if not isinstance(payload, dict) else payload)
        assert SECRET not in str(caught.value)
        assert caught.value.__cause__ is None

    obj = kr_overview()
    obj['rows'][0]['local']['value'] = SECRET
    with pytest.raises(ValueError, match='^invalid_currency_channel_input$'):
        call(obj)
    try:
        call(obj)
    except ValueError:
        tb = traceback.format_exc()
        assert SECRET not in tb
        assert tb.strip().endswith('ValueError: invalid_currency_channel_input')


def test_context_is_four_detached_fields_and_refs_name_exact_source():
    obj = load_overview()
    out = call(obj, 1)
    assert set(out) == OUTPUT_KEYS
    assert set(out['context']) == CONTEXT_KEYS
    assert 'source_reference_reason' not in out['context']
    assert out['context']['source_reference'] == 'synthetic:inspector-source'
    assert out['input_evidence_refs'] == [
        {'source_reference': 'synthetic:inspector-source', 'slot': 1, 'leg': 'local'},
        {'source_reference': 'synthetic:inspector-source', 'slot': 1, 'leg': 'usd'},
    ]
    json.dumps(out, allow_nan=False)


def test_korean_literals_are_percent_fx_and_percentage_point_contribution():
    obj = kr_overview()
    out = call(obj)
    assert out['local_return']['value'] == pytest.approx(-1.8)
    assert out['usd_return']['value'] == pytest.approx(-2.5856)
    assert out['fx_contribution_pp']['value'] == pytest.approx(-0.7856)
    assert out['fx_return_usd_per_local']['value'] == pytest.approx(-0.8)
    assert out['fx_return_usd_per_local']['value'] != pytest.approx(-0.7856)
    assert out['arithmetic_quality'] == 'qualified'
    assert out['reason'] is None
