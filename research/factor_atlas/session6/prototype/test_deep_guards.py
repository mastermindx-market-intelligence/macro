"""Additional corruption and metamorphic tests for S6's research-only guard."""
from dataclasses import replace, asdict
from decimal import Decimal as D, localcontext
from itertools import permutations
import pytest
import structural_guards as g
from test_structural_guards import valid

CLOCKS = ['minute_start_ns','minute_end_ns','cutoff_ns','source_known_ns',
          'reader_complete_ns','membership_known_ns','label_start_ns',
          'label_end_ns','last_correction_known_ns']
BAD_CLOCKS = [float('nan'),float('inf'),1.5,True,'1']

@pytest.mark.parametrize('field',CLOCKS)
@pytest.mark.parametrize('bad',BAD_CLOCKS)
def test_exact_clock_types(field,bad):
    assert g.assess_minute(valid(**{field:bad})).status == g.BLOCKED

@pytest.mark.parametrize('field',['minute_start_ns','minute_end_ns','cutoff_ns'])
def test_missing_mandatory_clock_is_typed(field):
    assert g.assess_minute(valid(**{field:None})).status == g.BLOCKED

@pytest.mark.parametrize('field',['factor_id','security_id','revision_id','monetary_basis_id','corporate_action_vintage'])
@pytest.mark.parametrize('bad',['',' ',123,None,[]])
def test_invalid_identity_does_not_use_truthiness(field,bad):
    assert g.assess_minute(valid(**{field:bad})).status == g.BLOCKED

@pytest.mark.parametrize('rows',[None,[],[None],['not_a_record']])
def test_empty_or_malformed_population_stays_null(rows):
    r=g.aggregate_synthetic(rows)
    assert r.status==g.BLOCKED
    assert r.unique_raw_gross is None
    assert r.duplicated_raw_gross is None

@pytest.mark.parametrize('field,new',[('revision_id','r1'),('monetary_basis_id','raw2'),
                                     ('corporate_action_vintage','ca-v2'),('signed_pressure',D('-45'))])
def test_conflicting_shared_source(field,new):
    r=g.aggregate_synthetic([valid(),valid(factor_id='SEMIS',**{field:new})])
    assert 'CONFLICTING_SHARED_MEMBER_SOURCE' in r.reasons

def test_mixed_cutoffs_not_one_observation():
    r=g.aggregate_synthetic([valid(),valid(factor_id='SEMIS',cutoff_ns=13*60_000_000_000,
                label_start_ns=14*60_000_000_000)])
    assert 'MIXED_CUTOFFS' in r.reasons

@pytest.mark.parametrize('prec',[7,28,40])
def test_pressure_bound_does_not_round_before_comparison(prec):
    with localcontext() as ctx:
        ctx.prec=prec
        r=g.assess_minute(valid(gross_notional=D('10000000000000000000000000000'),
                              signed_pressure=D('10000000000000000000000000001')))
    assert 'SIGN_EXCEEDS_GROSS' in r.reasons

@pytest.mark.parametrize('order',list(permutations(range(3))))
@pytest.mark.parametrize('prec',[7,28,40])
def test_money_sum_exact_and_permutation_invariant(order,prec):
    values=[D('10000000000000000000000000000'),D(5),D(5)]
    rows=[valid(security_id=str(i),gross_notional=v,signed_pressure=D(0),weight=D(1)) for i,v in enumerate(values)]
    with localcontext() as ctx:
        ctx.prec=prec
        r=g.aggregate_synthetic([rows[i] for i in order])
    expected=D('10000000000000000000000000010')
    assert r.status==g.NOT_ADMITTED and r.unique_raw_gross==expected
    assert dict(r.per_factor_allocated)['AI']==expected
    assert r.duplicated_raw_gross==0


def past(): return [g.BaselineObservation(str(i),i,D(i*i+1)) for i in range(20)]

@pytest.mark.parametrize('floor',[0,1,-1,True,1.5,g.MAX_RECORDS+1])
def test_baseline_floor_input_validation(floor):
    assert g.check_prior_baseline('now',1000,past(),min_history=floor).status==g.BLOCKED

@pytest.mark.parametrize('bad',BAD_CLOCKS+[None])
def test_baseline_cutoff_cannot_bypass(bad):
    assert g.check_prior_baseline('now',bad,past()).status==g.BLOCKED

@pytest.mark.parametrize('bad',BAD_CLOCKS+[None])
def test_baseline_known_clock_cannot_bypass(bad):
    rows=past();rows[0]=replace(rows[0],known_ns=bad)
    assert g.check_prior_baseline('now',1000,rows).status==g.BLOCKED


def quote(**changes):
    r=g.PrintQuoteClaim(100000,99000,100500,101000,10000,
      'ELIGIBLE_REGULAR','FINAL_UNCORRECTED',D('22'))
    return replace(r,**changes)

@pytest.mark.parametrize('field',['print_time_ns','quote_time_ns','source_receipt_ns','cutoff_ns','quote_age_limit_ns'])
@pytest.mark.parametrize('bad',BAD_CLOCKS)
def test_quote_exact_clock_and_age(field,bad):
    assert g.assess_quote_reference(quote(**{field:bad})).status==g.BLOCKED

@pytest.mark.parametrize('field',['print_time_ns','cutoff_ns','quote_age_limit_ns'])
def test_quote_missing_mandatory_clock(field):
    assert g.assess_quote_reference(quote(**{field:None})).status==g.BLOCKED

@pytest.mark.parametrize('value',[D('1e129'),D('1e-129'),D('9'*129)])
def test_declared_numeric_resource_limits(value):
    assert g.assess_minute(valid(gross_notional=value)).status==g.BLOCKED

@pytest.mark.parametrize('value',[True,'1',float('nan'),None])
def test_brier_typed_label(value):
    r=g.brier_diagnostic_only([g.LossRow('x',value,D('.5'),D('.6'))])
    assert r.status==g.BLOCKED

@pytest.mark.parametrize('value',[' ',[],123,None])
def test_brier_typed_identity(value):
    r=g.brier_diagnostic_only([g.LossRow(value,1,D('.5'),D('.6'))])
    assert r.status==g.BLOCKED


def test_research_only_flags_and_positive_controls():
    outputs=[g.assess_minute(valid()),g.assess_quote_reference(quote()),
             g.check_prior_baseline('now',1000,past()),g.aggregate_synthetic([valid()]),
             g.brier_diagnostic_only([g.LossRow('x',1,D('.5'),D('.6'))])]
    for o in outputs:
        assert o.status==g.NOT_ADMITTED
        for name,value in asdict(o).items():
            if name.endswith('_authorized') or name.endswith('_authenticated') or name=='rights_approved':
                assert value is False
