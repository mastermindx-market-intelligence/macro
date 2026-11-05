"""Qualified nominal point comparisons retain sign, units and evidence identity."""
from copy import deepcopy
from fractions import Fraction
import json

import pytest
from engine import intl_rates as owner

SLOTS = ('a_start', 'a_end', 'b_start', 'b_end')


def fixture(values=(.5, .5, 3.5, 3.0)):
    intent = dict(economy_a='JP', economy_b='US', lens='nominal_policy_point_gap',
                  definition='absolute_gap_change_bp', method_version='nominal-point/v1',
                  period=dict(mode='fixed_dates', start='2026-08-31', end='2026-09-30'),
                  vintage_policy='latest_vintage', identity=dict(principal_partition=None,
                  saved_id=None, saved_revision=None, source_generation='generation-1'))
    obs = {}
    for slot, value in zip(SLOTS, values):
        economy = intent['economy_'+slot[0]]
        obs[slot] = dict(economy=economy, instrument_id=economy+'-point',
                         instrument_kind='nominal_policy_point', observation_at=intent['period'][slot.split('_')[1]],
                         unit='percent', value=value, quality='qualified', metadata='allowed',
                         value_permission='allowed', source_reference='public/'+slot, qualification_ref='qualified/'+slot)
    mapping = dict(status='qualified', method_version=intent['method_version'], instruments={
        side: {key: obs[side+'_start'][key] for key in ('economy','instrument_id','instrument_kind')}
        for side in ('a','b')})
    return intent, obs, mapping


def run(values=(.5,.5,3.5,3.0)):
    return owner.compare_policy_points(*fixture(values))


def test_sample_preserves_signed_increase_and_absolute_narrowing():
    x=run()
    assert x['state']=='qualified'
    assert [x[k] for k in ('signed_start_bp','signed_end_bp','signed_change_bp','absolute_change_bp')] == [-300,-250,50,-50]
    assert x['direction']=='narrowed' and x['crosses_zero'] is False
    assert [r['slot'] for r in x['evidence_refs']]==list(SLOTS)
    json.dumps(x, allow_nan=False)


def test_swapped_pair_reverses_sign_not_absolute_direction():
    x=run();y=run((3.5,3.0,.5,.5))
    for key in ('signed_start_bp','signed_end_bp','signed_change_bp'):assert x[key]==-y[key]
    assert x['absolute_change_bp']==y['absolute_change_bp']
    assert x['direction']==y['direction']


@pytest.mark.parametrize('values,direction,crossing', [
    ((0,0,0,0),'unchanged_at_endpoints',False),
    ((-2,-3,-1,-1),'widened',False),
    ((-1,1,0,0),'unchanged_at_endpoints',True),
    ((0,1,0,0),'widened',False),
    ((1,0,0,0),'narrowed',False),
])
def test_negative_zero_crossing_and_touch_are_not_conflated(values,direction,crossing):
    x=run(values);assert x['state']=='qualified';assert x['direction']==direction;assert x['crosses_zero']==crossing


def test_mixed_percent_and_bp_normalizes_each_once():
    i,o,m=fixture()
    o['a_start'].update(unit='bp',value=50)
    o['b_end'].update(unit='bp',value=300)
    assert owner.compare_policy_points(i,o,m)==run()


def test_small_difference_is_not_rounded_to_false_flat():
    values=(1.0,1.0000000000000002,1.0,1.0)
    x=run(values);expected=float(100*(Fraction(values[1])-1))
    assert x['state']=='qualified' and x['signed_change_bp']==expected>0
    assert x['direction']=='widened'


@pytest.mark.parametrize('values', [(10**400,10**400,10**400,10**400), (10**400,10**400+1,10**400,10**400), (1e308,1e308,1e308,1e308)])
def test_large_finite_cancellation_is_exact_without_float_overflow(values):
    x=run(values);assert x['state']=='qualified'
    assert x['signed_change_bp']==100*(values[1]-values[0])
    json.dumps(x,allow_nan=False)


def test_non_integral_float_overflow_is_unavailable():
    x=run((1e308,1e308,0.1,0.1))
    assert x['state']=='unavailable' and x['reasons']==['arithmetic_unrepresentable']


@pytest.mark.parametrize('bad',[True,False,float('nan'),float('inf'),-float('inf'),'1',None,[],{}])
def test_invalid_numeric_is_fixed_error_without_raw_echo(bad):
    i,o,m=fixture();o['a_start']['value']=bad
    assert owner.compare_policy_points(i,o,m)==dict(state='invalid',identity=None,reasons=['invalid_policy_comparison'],missing_refs=[])


@pytest.mark.parametrize('field,bad', [('economy_a','US'),('economy_b','jp'),('lens','real_rate'),('definition','signed'),('method_version','')])
def test_invalid_intent(field,bad):
    i,o,m=fixture();i[field]=bad;assert owner.compare_policy_points(i,o,m)['state']=='invalid'


@pytest.mark.parametrize('date', ['2026-02-29','2026-13-01','2026-8-31','2026-08-31T00:00:00Z','2026-08-31 '])
def test_malformed_date_is_not_a_timestamp_or_guessed_cutoff(date):
    i,o,m=fixture();i['period']['start']=date;assert owner.compare_policy_points(i,o,m)['state']=='invalid'


def test_date_order_is_invalid_and_same_valid_date_requires_matching_endpoints():
    i,o,m=fixture();i['period']['end']='2026-08-30';assert owner.compare_policy_points(i,o,m)['state']=='invalid'
    i,o,m=fixture();i['period']['end']=i['period']['start']
    for key in ('a_end','b_end'):
        o[key]['observation_at']=i['period']['end']
        o[key]['value']=o[key[0]+'_start']['value']
    assert owner.compare_policy_points(i,o,m)['state']=='qualified'


@pytest.mark.parametrize('slot',SLOTS)
def test_missing_slot_withholds_all_values_and_refs(slot):
    i,o,m=fixture();o[slot]=None;x=owner.compare_policy_points(i,o,m)
    assert x['state']=='unavailable' and x['missing_refs']==[slot]
    assert not {'signed_start_bp','evidence_refs'} & x.keys()


@pytest.mark.parametrize('field,value', [('quality','stale'),('metadata','denied'),('metadata','unknown'),('value_permission','denied'),('instrument_kind','effective_rate'),('instrument_kind','target_range'),('economy','GB'),('instrument_id','wrong-point'),('observation_at','2026-08-30')])
def test_unqualified_or_wrong_bound_endpoint_is_not_an_answer(field,value):
    i,o,m=fixture();o['a_start'][field]=value;o['a_start']['source_reference']='PRIVATE-SENTINEL';x=owner.compare_policy_points(i,o,m)
    assert x['state']=='unavailable';assert x['missing_refs']==['a_start'];assert 'PRIVATE-SENTINEL' not in json.dumps(x)
    assert 'evidence_refs' not in x


@pytest.mark.parametrize('mutate', [lambda m:m.update(status='denied'), lambda m:m.update(method_version='wrong'),lambda m:m['instruments']['a'].update(economy='GB'),lambda m:m['instruments']['a'].update(instrument_kind='target_midpoint')])
def test_mapping_assertion_must_match_every_dimension(mutate):
    i,o,m=fixture();mutate(m);assert owner.compare_policy_points(i,o,m)['state']=='unavailable'


def test_missing_mapping_and_unsupported_vintages_do_not_fabricate_comparability():
    i,o,m=fixture();assert owner.compare_policy_points(i,o,None)['reasons']==['mapping_not_supplied']
    i['vintage_policy']='original_known';x=owner.compare_policy_points(i,o,m);assert x['state']=='unavailable';assert x['reasons']==['original_known_unavailable']


def test_owner_horizon_is_not_silently_converted_to_fixed_dates():
    i,o,m=fixture();i['period']={'mode':'owner_horizon','key':'1m'}
    x=owner.compare_policy_points(i,o,m);assert x['state']=='unavailable';assert x['reasons']==['unsupported_period_mode']


def test_identity_exact_copy_and_no_input_or_output_aliases():
    i,o,m=fixture();before=deepcopy((i,o,m));x=owner.compare_policy_points(i,o,m)
    assert x['identity']==i and (i,o,m)==before
    x['identity']['period']['start']='changed';x['evidence_refs'][0]['source_reference']='changed'
    assert (i,o,m)==before


@pytest.mark.parametrize('mutate', [lambda i,o,m:i.update(extra='PRIVATE'),lambda i,o,m:o.update(extra=None),lambda i,o,m:o['a_start'].update(extra='PRIVATE'),lambda i,o,m:m.update(extra='PRIVATE'),lambda i,o,m:i['identity'].update(saved_revision=True),lambda i,o,m:i['identity'].update(saved_revision=0),lambda i,o,m:o['a_start'].update(unit='USD'),lambda i,o,m:i.update(economy_a=i)])
def test_unknown_shapes_and_cycles_are_fixed_invalid(mutate):
    i,o,m=fixture();mutate(i,o,m);x=owner.compare_policy_points(i,o,m)
    assert x==dict(state='invalid',identity=None,reasons=['invalid_policy_comparison'],missing_refs=[])


def test_same_endpoint_cannot_claim_two_latest_values():
    i,o,m=fixture();i['period']['end']=i['period']['start']
    for key in ('a_end','b_end'):o[key]['observation_at']=i['period']['end']
    x=owner.compare_policy_points(i,o,m)
    assert x['state']=='unavailable' and x['reasons']==['observation_conflict']
    assert x['missing_refs']==['b_start','b_end']


def test_identity_unrepresentable_as_json_is_fixed_invalid():
    i,o,m=fixture();i['identity']['saved_revision']=10**5000
    x=owner.compare_policy_points(i,o,m)
    assert x['state']=='invalid'
    json.dumps(x,allow_nan=False)


def test_same_endpoint_mixed_units_is_not_a_conflict():
    i,o,m=fixture((.5,.5,3.0,3.0));i['period']['end']=i['period']['start']
    for key in ('a_end','b_end'):o[key]['observation_at']=i['period']['end']
    o['a_end'].update(value=50,unit='bp')
    x=owner.compare_policy_points(i,o,m)
    assert x['state']=='qualified' and x['signed_change_bp']==0
