"""Currency explanation contracts, using an actual synthetic Overview projection."""
import copy
import json
import math
from pathlib import Path
import pytest
from lib.intl_workspace_risk_currency import build_currency_channel

FIXTURE = Path(__file__).parent / 'fixtures/intl_workspace/risk_currency_overview.json'


def projection(local=-1.8, usd=-2.5856, contribution=-0.7856):
    obj = json.loads(FIXTURE.read_text())
    obj['focus_ids'] = ['GB']  # Keep the unmodified disclosed row as the focus.
    row = obj['rows'][0]
    row.update(market_id='KR', name_en='South Korea', name_zh='韩国', index_id='^KS11', index_label='KOSPI')
    for leg, value in [('local',local), ('usd',usd), ('fx_contribution',contribution)]:
        row[leg]['value'] = value
    row['metric'] = copy.deepcopy(row['usd'])
    return obj


def call(obj):
    return build_currency_channel(obj, selected_slot=0)


def withhold(obj, leg, quality='unknown'):
    obj['rows'][0][leg].update(value=None, quality=quality, reason='value_denied' if quality=='denied' else 'qualification_unknown', window=None)
    obj['rows'][0]['metric'] = copy.deepcopy(obj['rows'][0]['usd'])


def test_korean_example_separates_raw_fx_from_contribution():
    obj=projection();out=call(obj)
    assert out['arithmetic_quality']=='qualified'
    assert out['local_return']==obj['rows'][0]['local']
    assert out['usd_return']==obj['rows'][0]['usd']
    assert out['fx_contribution_pp']==obj['rows'][0]['fx_contribution']
    assert out['fx_return_usd_per_local']['value']==pytest.approx(-0.8)
    assert out['fx_return_usd_per_local']['unit']=='percent'
    assert out['fx_return_usd_per_local']['derivation']=='derived_from_disclosed_returns'
    assert out['endpoint_policy']==obj['rows'][0]['usd']['window']
    assert out['input_evidence_refs']==[{'source_reference':'synthetic:inspector-source','slot':0,'leg':'local'}, {'source_reference':'synthetic:inspector-source','slot':0,'leg':'usd'}]


@pytest.mark.parametrize('local,usd,contribution,fx', [(0,0,0,0),(-0.0,-0.0,-0.0,0),(10,21,11,10),(10,-1,-11,-10),(-50,-25,25,50),(0,-100,-100,-100)])
def test_unrounded_positive_negative_zero_and_complete_loss(local,usd,contribution,fx):
    out=call(projection(local,usd,contribution))
    assert out['arithmetic_quality']=='qualified'
    assert out['fx_return_usd_per_local']['value']==pytest.approx(fx)
    assert math.copysign(1,out['local_return']['value'])==math.copysign(1,local)


@pytest.mark.parametrize('leg', ['local','usd'])
def test_valid_independent_return_survives_missing_other_leg(leg):
    obj=projection();withhold(obj,leg);out=call(obj)
    other='usd_return' if leg=='local' else 'local_return'
    assert out[other]['quality']=='qualified'
    assert out['fx_return_usd_per_local']['value'] is None
    assert out['arithmetic_quality']=='partial'
    assert out['endpoint_policy'] is None and out['input_evidence_refs']==[]


@pytest.mark.parametrize('part,value', [('start','2025-12-19T00:00:00'),('end','2026-01-09T00:00:00'),('calendar_policy','different'),('price_start','2025-12-17T00:00:00'),('price_end','2026-01-07T00:00:00')])
def test_unequal_price_window_withholds_derivation(part,value):
    obj=projection();w=obj['rows'][0]['local']['window']
    (w['endpoint_observations'] if part.startswith('price_') else w)[part]=value
    out=call(obj)
    assert out['fx_return_usd_per_local']['quality']=='unknown'
    assert out['arithmetic_quality']=='partial' and out['endpoint_policy'] is None


@pytest.mark.parametrize('local,usd', [(-100,0),(-101,0),(0,-101),(10**400,1),(1,10**400),(-99.99999999999999,1e308)])
def test_invalid_denominator_or_nonfinite_arithmetic_is_withheld(local,usd):
    out=call(projection(local,usd,0))
    assert out['fx_return_usd_per_local']['value'] is None
    assert out['arithmetic_quality']=='partial'


def test_explicit_fx_denial_is_not_bypassed_with_derivation():
    obj=projection();withhold(obj,'fx_contribution','denied');out=call(obj)
    assert out['local_return']['quality']==out['usd_return']['quality']=='qualified'
    assert out['fx_return_usd_per_local']['value'] is None
    assert out['input_evidence_refs']==[]


def test_wrong_owner_contribution_stays_visible_and_is_not_repaired():
    out=call(projection(contribution=99))
    assert out['fx_contribution_pp']['value']==99
    assert out['arithmetic_quality']=='partial' and out['reason']=='contribution_mismatch'
    assert out['fx_return_usd_per_local']['value']==pytest.approx(-0.8)


def test_no_source_cannot_support_derivation():
    obj=projection();obj['context']['source_reference']=None;obj['context']['source_reference_reason']='source_unknown'
    out=call(obj)
    assert out['fx_return_usd_per_local']['value'] is None and out['input_evidence_refs']==[]


def test_redacted_slot_has_no_borrowed_identity_values_or_source():
    obj=projection();obj['rows'][0]={'slot':0,'quality':'denied','reason':'metadata_denied'}
    out=call(obj)
    assert out['market'] is None and out['context']['source_reference'] is None
    assert out['arithmetic_quality']=='unavailable'
    assert all(out[k]['value'] is None for k in ('local_return','usd_return','fx_return_usd_per_local','fx_contribution_pp'))
    assert 'KR' not in json.dumps(out) and 'synthetic' not in json.dumps(out)


def test_no_usable_return_clears_context_reference():
    obj=projection();withhold(obj,'local');withhold(obj,'usd');withhold(obj,'fx_contribution')
    out=call(obj)
    assert out['context']['source_reference'] is None and out['arithmetic_quality']=='unavailable'


@pytest.mark.parametrize('slot', [True,-1,2,'0',None])
def test_invalid_selection_has_fixed_error(slot):
    with pytest.raises(ValueError, match='^invalid_currency_channel_input$'):
        build_currency_channel(projection(), selected_slot=slot)


@pytest.mark.parametrize('value', [float('nan'),float('inf'),True,'secret'])
def test_invalid_value_has_fixed_error(value):
    with pytest.raises(ValueError, match='^invalid_currency_channel_input$'):
        call(projection(local=value))


def test_wrong_unit_is_not_reinterpreted():
    obj=projection();obj['rows'][0]['local']['unit']='fraction'
    with pytest.raises(ValueError, match='^invalid_currency_channel_input$'):call(obj)


def test_hostile_input_never_invokes_hooks():
    class Hostile(dict):
        def get(self,*args):raise AssertionError('custom code invoked')
    with pytest.raises(ValueError, match='^invalid_currency_channel_input$'):call(Hostile(projection()))


def test_detached_output_and_actual_owner_fixture_compatibility():
    obj=json.loads(FIXTURE.read_text());before=copy.deepcopy(obj);out=call(obj)
    assert out['arithmetic_quality']=='qualified' and obj==before
    out['local_return']['window']['start']='changed'
    out['market']['name_en']='changed'
    assert obj==before


def test_contribution_must_share_the_same_price_window():
    obj=projection();obj['rows'][0]['fx_contribution']['window']['endpoint_observations']['price_end']='2026-01-07T00:00:00'
    out=call(obj)
    assert out['arithmetic_quality']=='partial' and out['fx_return_usd_per_local']['quality']=='qualified'


@pytest.mark.parametrize('local', [10**300, 1e308])
def test_float_collapse_is_not_a_qualified_total_currency_loss(local):
    out=call(projection(local=local, usd=0, contribution=-local))
    assert out['fx_return_usd_per_local']['value'] is None
    assert out['arithmetic_quality']=='partial' and out['reason']=='numerical_unavailable'
    assert out['local_return']['value']==local and out['usd_return']['value']==0
