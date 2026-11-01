"""R2 independent countercases for the one-condition FX collapse withhold.

Does not import author tests. Retained independent_tests.py is unchanged.
"""
import copy
import json
import math
from pathlib import Path

import pytest

from lib.intl_workspace_risk_currency import build_currency_channel

FIXTURE = Path(__file__).parent / 'fixtures/intl_workspace/risk_currency_overview.json'


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




def assert_no_nonfinite(obj, path='out'):
    if isinstance(obj, float):
        assert math.isfinite(obj), path
    elif isinstance(obj, dict):
        for key, value in obj.items():
            assert_no_nonfinite(value, path + '.' + key)
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            assert_no_nonfinite(value, f'{path}[{index}]')


@pytest.mark.parametrize('local,contribution', [
    (25, -125),
    (0, -100),
    (-50, -50),
])
def test_legitimate_usd_complete_loss_remains_qualified(local, contribution):
    obj = kr_overview(local=local, usd=-100, contribution=contribution)
    before = copy.deepcopy(obj)
    out = call(obj)
    assert out['fx_return_usd_per_local']['value'] == pytest.approx(-100)
    assert out['fx_return_usd_per_local']['quality'] == 'qualified'
    assert out['fx_return_usd_per_local']['derivation'] == 'derived_from_disclosed_returns'
    assert out['arithmetic_quality'] == 'qualified'
    assert out['reason'] is None
    assert out['local_return']['value'] == local
    assert out['usd_return']['value'] == -100
    assert out['fx_contribution_pp']['value'] == contribution
    assert out['endpoint_policy'] is not None
    assert obj == before
    assert_no_nonfinite(out)


@pytest.mark.parametrize('local,usd', [(-99.9, 0), (-99.999, 1), (-99.99999999999999, 0)])
def test_local_near_minus_100_does_not_divide_by_zero(local, usd):
    obj = kr_overview(local=local, usd=usd, contribution=usd - local)
    out = call(obj)
    fx = out['fx_return_usd_per_local']['value']
    assert fx is not None
    assert math.isfinite(fx)
    assert fx != -100
    assert out['arithmetic_quality'] == 'qualified'
    assert out['local_return']['value'] == local
    assert out['usd_return']['value'] == usd
    assert_no_nonfinite(out)


@pytest.mark.parametrize('local,usd', [(10 ** 300, 0), (1e308, 0), (10 ** 300, -50)])
def test_finite_extreme_collapse_is_partial_without_derived_value(local, usd):
    contribution = usd - local
    obj = kr_overview(local=local, usd=usd, contribution=contribution)
    before = copy.deepcopy(obj)
    out = call(obj)
    assert out['fx_return_usd_per_local']['value'] is None
    assert out['fx_return_usd_per_local']['quality'] == 'unknown'
    assert out['arithmetic_quality'] == 'partial'
    assert out['reason'] == 'numerical_unavailable'
    assert out['endpoint_policy'] is None
    assert out['input_evidence_refs'] == []
    assert out['local_return']['value'] == local
    assert out['local_return']['quality'] == 'qualified'
    assert out['usd_return']['value'] == usd
    assert out['usd_return']['quality'] == 'qualified'
    assert out['fx_contribution_pp']['value'] == contribution
    assert obj == before
    assert_no_nonfinite(out)


def test_independently_qualified_owner_values_survive_collapse_withhold():
    local = 10 ** 300
    obj = kr_overview(local=local, usd=0, contribution=99)
    out = call(obj)
    assert out['local_return']['value'] == local
    assert out['usd_return']['value'] == 0
    assert out['fx_contribution_pp']['value'] == 99
    assert out['fx_return_usd_per_local']['value'] is None
    assert out['arithmetic_quality'] == 'partial'
    assert out['reason'] == 'numerical_unavailable'


