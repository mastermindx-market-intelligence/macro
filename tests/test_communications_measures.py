"""Pure A1 contract tests. All receipts/identities below are SYNTHETIC.

The frozen CV numbers are documentary regression examples, not current sources,
owner admission, entitlement proof, or a production four-company release.
"""
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal as D, localcontext

import pytest

from engine.market_ontology.communications_measures import (
    CashComponent, CashRole, ComparisonRule, Guidance, InputBinding, Interval,
    Measure, cash_bridge, compare_guidance, compare_period,
)

PERIOD = ('2026-04-01', '2026-06-30')
PRIOR = ('2025-04-01', '2025-06-30')


def measure(value='100', *, ref='fixture:actual', **changes):
    value = None if value is None else D(value)
    point = None if value is None else Interval(value, value, True, True)
    m = Measure(ref, 'revenue', 'fixture:issuer', PERIOD, 'USD', D('1'),
                'reported_gaap', value, 'nonnegative_amount', 'fixture:definition',
                'currency', point, 'exact' if value is not None else 'unknown', None)
    return replace(m, **changes)


def guidance(lower='100', upper=None, **changes):
    g = Guidance('fixture:guide', 'revenue', 'fixture:issuer', PERIOD, 'USD', D('1'),
                 'reported_gaap', None if lower is None else D(lower),
                 None if upper is None else D(upper),
                 None if lower is None else True, None if upper is None else True,
                 '2026-04-29', 'original_company_guidance', 'fixture:definition',
                 'currency', 'stated_threshold')
    return replace(g, **changes)


def rule(operation, *inputs, **changes):
    bindings = tuple(InputBinding(role, m.ref, m.definition_ref, m.population,
                                 m.period, m.unit, m.currency, m.scale,
                                 getattr(m, 'domain', 'nonnegative_amount'))
                     for role, m in inputs)
    return replace(ComparisonRule('fixture:rule-v1', operation, bindings,
                                 'fixture:reviewed-relation', 'fixture:review',
                                 'underlying_interval', ()), **changes)


def period_rule(current, prior, mode='pct', **changes):
    return rule('period_pct' if mode == 'pct' else 'period_absolute',
                ('current', current), ('prior', prior), **changes)


def guide_rule(actual, guide, **changes):
    return rule('guidance', ('actual', actual), ('guide', guide), **changes)


def cash_case(*, outflow='60', signed=False, cfo='100'):
    a = measure(cfo, ref='fixture:cfo', metric='cash', domain='signed_amount')
    b = measure(outflow, ref='fixture:capex', metric='cash',
                domain='signed_amount' if signed else 'nonnegative_amount')
    orientation = 'signed_flow' if signed else 'positive_magnitude'
    coefficient = 1 if signed else -1
    roles = (CashRole('operating_cash', 'cfo', 'signed_flow', 1),
             CashRole('capital_investment', 'capex', orientation, coefficient))
    components = (CashComponent('operating_cash', a.ref, 'signed_flow', 1),
                  CashComponent('capital_investment', b.ref, orientation, coefficient))
    r = rule('cash', ('cfo', a), ('capex', b), cash_roles=roles)
    return (a, b), components, r


def test_rounding_does_not_become_an_exact_guidance_verdict():
    a = measure(support=Interval(D('99.5'), D('100.5'), True, True),
                support_basis='reviewed_nearest', support_ref='fixture:rounding-review')
    g = guidance()
    result = compare_guidance(a, g, rule=guide_rule(a, g))
    assert result.status == 'QUALIFIED'
    assert result.label == 'ROUNDING_INDETERMINATE'
    assert result.value is None
    assert result.refs == (a.ref, g.ref)
    assert result.rule_revision == 'fixture:rule-v1'
    assert result.interpretation_basis == 'underlying_interval'


@pytest.mark.parametrize('value,lower,upper,li,ui,label', [
    ('100','100',None,True,None,'MEETS_ORIGINAL_FLOOR'),
    ('100','100',None,False,None,'AT_EXCLUDED_BOUNDARY'),
    ('99','100',None,False,None,'BELOW_ORIGINAL_FLOOR'),
    ('101','100',None,False,None,'MEETS_ORIGINAL_FLOOR'),
    ('100',None,'100',None,True,'WITHIN_ORIGINAL_CEILING'),
    ('100',None,'100',None,False,'AT_EXCLUDED_BOUNDARY'),
    ('101',None,'100',None,True,'ABOVE_ORIGINAL_CEILING'),
    ('100','90','110',True,True,'WITHIN_ORIGINAL_RANGE'),
])
def test_guidance_boundaries(value, lower, upper, li, ui, label):
    a = measure(value)
    g = guidance(lower, upper, lower_inclusive=li, upper_inclusive=ui)
    out = compare_guidance(a, g, rule=guide_rule(a, g))
    assert (out.status, out.label) == ('COMPARABLE', label)


@pytest.mark.parametrize('lo,hi,li,ui,expected', [
    ('100','101',False,True,'MEETS_ORIGINAL_FLOOR'),
    ('99','100',True,False,'BELOW_ORIGINAL_FLOOR'),
    ('99','100',True,True,'ROUNDING_INDETERMINATE'),
    ('100','101',True,True,'ROUNDING_INDETERMINATE'),
])
def test_supported_open_intervals_do_not_invent_boundary_equality(lo, hi, li, ui, expected):
    a = measure(None, support=Interval(D(lo), D(hi), li, ui),
                support_basis='source_interval', support_ref='fixture:source-interval')
    g = guidance(lower_inclusive=False)
    out = compare_guidance(a, g, rule=guide_rule(a, g))
    assert out.label == expected
    assert out.status == ('QUALIFIED' if expected == 'ROUNDING_INDETERMINATE' else 'COMPARABLE')


def test_unknown_precision_has_no_underlying_point_support():
    a = measure(support=None, support_basis='unknown')
    g = guidance()
    out = compare_guidance(a, g, rule=guide_rule(a, g))
    assert (out.status, out.label, out.value) == ('QUALIFIED', 'SOURCE_PRECISION_UNKNOWN', None)
    printed = compare_guidance(a, g, rule=guide_rule(a, g, interpretation_basis='published_figures'))
    assert (printed.status, printed.label) == ('QUALIFIED', 'MEETS_ORIGINAL_FLOOR')
    assert printed.reason == 'PUBLISHED_FIGURES_ONLY'


def test_scale_conversion_includes_uncertainty_not_only_display_value():
    a = measure('1500', scale=D('1000'),
                support=Interval(D('1499.5'), D('1500.5'), True, True),
                support_basis='reviewed_nearest', support_ref='fixture:rounding')
    g = guidance('1.5', scale=D('1000000'))
    out = compare_guidance(a, g, rule=guide_rule(a, g))
    assert out.label == 'ROUNDING_INDETERMINATE'
    exact = measure('1500', scale=D('1000'))
    assert compare_guidance(exact, g, rule=guide_rule(exact, g)).label == 'MEETS_ORIGINAL_FLOOR'


@pytest.mark.parametrize('bounds_basis', ['approximate', 'unknown'])
def test_approximate_outlook_does_not_become_a_threshold(bounds_basis):
    a, g = measure('90'), guidance(bounds_basis=bounds_basis)
    out = compare_guidance(a, g, rule=guide_rule(a, g))
    assert out.status == 'QUALIFIED'
    assert out.label == 'GUIDANCE_BOUNDS_UNQUALIFIED'
    assert out.value is None


# CV01/02/05/06/08/09/11: one fixed economic issuer per example; no ranking.
@pytest.mark.parametrize('case,current,prior,expected', [
    ('CV01-Meta-revenue','60801','47516','27.959003'),
    ('CV02-Meta-operating-income','18775','20441','-8.150286'),
    ('CV05-Alphabet-Search','63271','54190','16.757704'),
    ('CV06-Alphabet-Network','7303','7354','-0.693500'),
    ('CV08-TradeDesk-revenue','715057','694039','3.028360'),
    ('CV09-TradeDesk-operating-income','101577','116777','-13.016262'),
    ('CV11-Magnite-exTAC','189595','161956','17.065746'),
])
def test_four_company_frozen_documentary_arithmetic(case, current, prior, expected):
    a = measure(current, population='fixture:' + case)
    b = measure(prior, ref='fixture:prior', population=a.population, period=PRIOR)
    out = compare_period(a, b, rule=period_rule(a, b))
    assert out.status == 'COMPARABLE'
    assert out.value.quantize(D('0.000001')) == D(expected)
    assert out.label == 'PERCENT_CHANGE'
    assert out.refs == (a.ref, b.ref)
    assert out.formula == '100 * (current_scaled - prior_scaled) / prior_scaled'


@pytest.mark.parametrize('value,lower,upper,scale,label,distance', [
    ('60801','58000','61000','1','WITHIN_ORIGINAL_RANGE',None),
    ('715057','750',None,'1000','BELOW_ORIGINAL_FLOOR','-4.659067'),
    ('189595','175','181','1000','ABOVE_ORIGINAL_CEILING','4.748619'),
])
def test_cv04_cv10_cv12_original_guidance_not_consensus(value, lower, upper, scale, label, distance):
    a, g = measure(value), guidance(lower, upper, scale=D(scale))
    out = compare_guidance(a, g, rule=guide_rule(a, g))
    assert out.label == label
    assert out.status == 'COMPARABLE'
    assert (None if out.value is None else out.value.quantize(D('0.000001'))) == (None if distance is None else D(distance))
    assert 'consensus' not in out.label.lower()


@pytest.mark.parametrize('prior', ['0','-5'])
def test_nonpositive_prior_refuses_growth_but_preserves_absolute_change(prior):
    a = measure('10', domain='signed_amount')
    b = measure(prior, ref='fixture:prior', period=PRIOR, domain='signed_amount')
    out = compare_period(a, b, rule=period_rule(a,b))
    assert (out.status, out.reason, out.value) == ('UNAVAILABLE','NONPOSITIVE_PRIOR',None)
    absolute = compare_period(a,b,rule=period_rule(a,b,'absolute'),mode='absolute')
    assert absolute.status == 'COMPARABLE'
    assert absolute.value == D('10') - D(prior)


def test_missing_numeric_value_does_not_become_zero():
    a, b = measure(None), measure('80',ref='fixture:prior',period=PRIOR)
    out = compare_period(a,b,rule=period_rule(a,b))
    assert (out.status,out.reason,out.value) == ('UNAVAILABLE','POINT_VALUE_UNAVAILABLE',None)


@pytest.mark.parametrize('field,changed', [
    ('ref','fixture:corrected'), ('definition_ref','fixture:other-definition'),
    ('population','fixture:other-issuer'), ('period',('2026-07-01','2026-09-30')),
    ('unit','count'), ('currency','EUR'), ('scale',D('1000')),
    ('domain','signed_amount'),
])
def test_old_rule_cannot_silently_rebind_corrected_or_changed_input(field,changed):
    a, b = measure(), measure('80',ref='fixture:prior',period=PRIOR)
    r = period_rule(a,b)
    candidate = replace(a, **{field: changed})
    if field == 'unit':
        # Use a structurally valid count to isolate binding validation. A lone
        # count label on a USD monetary domain is already INVALID_MEASURE.
        candidate = replace(candidate, currency=None, domain='nonnegative_count')
    out = compare_period(candidate, b, rule=r)
    assert (out.status,out.reason) == ('INCOMPATIBLE','INPUT_BINDING_MISMATCH')
    assert out.rule_revision == r.revision
    assert out.value is None


@pytest.mark.parametrize('field,value,reason', [
    ('review_ref','','RULE_NOT_REVIEWED'),('relation_ref','','RULE_NOT_REVIEWED'),
    ('operation','cash','RULE_OPERATION_MISMATCH'),
])
def test_unreviewed_or_wrong_recipe_cannot_fall_back_to_labels(field,value,reason):
    a,b=measure(),measure('80',ref='fixture:prior',period=PRIOR)
    out=compare_period(a,b,rule=replace(period_rule(a,b),**{field:value}))
    assert out.reason == reason
    assert out.value is None


def test_missing_rule_returns_typed_unavailability():
    a,b=measure(),measure('80',ref='fixture:prior',period=PRIOR)
    out=compare_period(a,b,rule=None)
    assert (out.status,out.reason,out.rule_revision)==('UNAVAILABLE','RULE_REQUIRED','')


def test_different_definitions_require_exact_bound_reviewed_relation():
    a=measure(definition_ref='fixture:new-definition')
    b=measure('80',ref='fixture:prior',period=PRIOR)
    accepted=period_rule(a,b)
    assert compare_period(a,b,rule=accepted).value == D('25')
    assert compare_period(a,b,rule=replace(accepted,relation_ref='')).reason=='RULE_NOT_REVIEWED'


@pytest.mark.parametrize('change', [
    {'population':'fixture:other'}, {'currency':'EUR'}, {'metric':'gross_profit'},
    {'basis':'non_gaap'}, {'basis':''}, {'unit':'count'},
])
def test_even_rebound_inputs_do_not_erase_scope_or_accounting_mismatch(change):
    a=measure(**change)
    b=measure('80',ref='fixture:prior',period=PRIOR)
    out=compare_period(a,b,rule=period_rule(a,b))
    assert out.status=='INCOMPATIBLE'
    assert out.value is None


@pytest.mark.parametrize('unit,domain,current,prior,label', [
    ('percent','percent','5','4','PERCENTAGE_POINT_CHANGE'),
    ('fraction','fraction','0.05','0.04','FRACTIONAL_RATE_CHANGE'),
])
def test_rates_have_explicit_absolute_units_not_silent_percent_growth(unit,domain,current,prior,label):
    a=measure(current,unit=unit,domain=domain,currency=None)
    b=measure(prior,ref='fixture:prior',period=PRIOR,unit=unit,domain=domain,currency=None)
    assert compare_period(a,b,rule=period_rule(a,b)).reason=='RATE_PERCENT_CHANGE_UNSUPPORTED'
    out=compare_period(a,b,rule=period_rule(a,b,'absolute'),mode='absolute')
    assert (out.label,out.value)==(label,D(current)-D(prior))


@pytest.mark.parametrize('bad', [D('NaN'),D('sNaN'),D('Infinity'),D('-Infinity'),D('1e1000000'),D('1e-1000000'),True,1.5,'100'])
def test_malformed_decimal_is_refused_before_arithmetic(bad):
    a=measure(value=bad) if isinstance(bad,str) else replace(measure(),value=bad)
    # A raw string is intentionally not parsed by the production adapter.
    if isinstance(bad,str): a=replace(measure(),value=bad)
    b=measure('80',ref='fixture:prior',period=PRIOR)
    out=compare_period(a,b,rule=period_rule(a,b))
    assert (out.status,out.reason,out.value)==('INCOMPATIBLE','INVALID_MEASURE',None)


@pytest.mark.parametrize('scale',[D('0'),D('-1'),D('NaN'),True])
def test_invalid_scale_is_never_used(scale):
    a=measure(scale=scale)
    b=measure('80',ref='fixture:prior',period=PRIOR)
    assert compare_period(a,b,rule=period_rule(a,b)).reason=='INVALID_MEASURE'


@pytest.mark.parametrize('support', [Interval(D('101'),D('99'),True,True),Interval(D('100'),D('100'),False,True),Interval(D('99'),D('101'),True,True)])
def test_invalid_or_falsely_exact_support_is_refused(support):
    a,g=measure(support=support),guidance()
    assert compare_guidance(a,g,rule=guide_rule(a,g)).reason=='INVALID_MEASURE'


@pytest.mark.parametrize('signed,outflow',[ (False,'60'),(True,'-60') ])
def test_cash_orientation_is_bound_to_recipe_not_inferred_from_sign(signed,outflow):
    values,components,r=cash_case(signed=signed,outflow=outflow)
    out=cash_bridge(measures=values,components=components,rule=r)
    assert (out.status,out.value,out.label)==('COMPARABLE',D('40'),'CASH_BRIDGE')
    assert out.refs==tuple(m.ref for m in values)


def test_negative_positive_magnitude_refuses_instead_of_producing_160():
    values,components,r=cash_case(outflow='-60')
    out=cash_bridge(measures=values,components=components,rule=r)
    assert out.status=='INCOMPATIBLE'
    assert out.value is None


def test_cv07_alphabet_signed_consolidated_cash_is_not_search_cash():
    values,components,r=cash_case(cfo='39069',outflow='44924')
    out=cash_bridge(measures=values,components=components,rule=r)
    assert (out.status,out.value)==('COMPARABLE',D('-5855'))
    wrong=replace(values[0],population='fixture:Search-only')
    assert cash_bridge(measures=(wrong,values[1]),components=components,rule=r).reason=='INPUT_BINDING_MISMATCH'


def test_cv03_required_lease_principal_cannot_be_omitted():
    values,components,r=cash_case(cfo='31862',outflow='30116')
    lease=measure('962',ref='fixture:lease',metric='cash')
    all_values=values+(lease,)
    all_components=components+(CashComponent('lease_principal',lease.ref,'positive_magnitude',-1),)
    roles=r.cash_roles+(CashRole('lease_principal','lease','positive_magnitude',-1),)
    r=rule('cash',('cfo',values[0]),('capex',values[1]),('lease',lease),cash_roles=roles)
    assert cash_bridge(measures=all_values,components=all_components,rule=r).value==D('784')
    assert cash_bridge(measures=all_values,components=components,rule=r).reason=='CASH_RECIPE_MISMATCH'


@pytest.mark.parametrize('mutation',['duplicate_component','duplicate_receipt','extra_net_subtotal','wrong_sign'])
def test_cash_does_not_double_count_or_change_reviewed_partition(mutation):
    values,components,r=cash_case()
    if mutation=='duplicate_component': components=components+(components[1],)
    if mutation=='duplicate_receipt': values=values+(values[1],)
    if mutation=='extra_net_subtotal': components=components+(CashComponent('net_subtotal',values[0].ref,'signed_flow',1),)
    if mutation=='wrong_sign': components=(components[0],replace(components[1],coefficient=1))
    out=cash_bridge(measures=values,components=components,rule=r)
    assert out.status=='INCOMPATIBLE'
    assert out.value is None


def test_same_uncertain_input_cancels_only_under_explicit_reviewed_algebra():
    a=measure(None,ref='fixture:x',support=Interval(D('99'),D('101'),True,True),support_basis='source_interval',support_ref='fixture:interval')
    roles=(CashRole('x_add','add','signed_flow',1),CashRole('x_remove','remove','signed_flow',-1))
    components=(CashComponent('x_add',a.ref,'signed_flow',1),CashComponent('x_remove',a.ref,'signed_flow',-1))
    r=rule('cash',('add',a),('remove',a),cash_roles=roles)
    out=cash_bridge(measures=(a,),components=components,rule=r)
    assert (out.status,out.value)==('COMPARABLE',D('0'))


def test_local_decimal_context_and_input_objects_are_not_mutated():
    a,b=measure('60801'),measure('47516',ref='fixture:prior',period=PRIOR)
    r=period_rule(a,b)
    before=(a,b,r)
    expected=compare_period(a,b,rule=r)
    with localcontext() as ctx:
        ctx.prec=3
        actual=compare_period(a,b,rule=r)
        assert ctx.prec==3
    assert actual==expected
    assert before==(a,b,r)
    assert actual.value.quantize(D('0.000001'))==D('27.959003')
    with pytest.raises(FrozenInstanceError): a.value=D('0')


@pytest.mark.parametrize('domain', [[], {}, ['signed_amount']])
def test_malformed_measure_domain_returns_typed_refusal(domain):
    a = replace(measure(), domain=domain)
    b = measure('80', ref='fixture:prior', period=PRIOR)
    out = compare_period(a, b, rule=period_rule(a, b))
    assert (out.status, out.reason, out.value) == ('INCOMPATIBLE', 'INVALID_MEASURE', None)


@pytest.mark.parametrize('domain', [[], {}, ['signed_amount']])
def test_malformed_rule_domain_returns_typed_refusal(domain):
    a, g = measure(), guidance()
    r = guide_rule(a, g)
    r = replace(r, bindings=(replace(r.bindings[0], domain=domain), r.bindings[1]))
    out = compare_guidance(a, g, rule=r)
    assert (out.status, out.reason, out.value) == ('INCOMPATIBLE', 'INPUT_BINDING_MISMATCH', None)


def test_count_label_on_monetary_domain_refuses_before_rule_binding():
    a = replace(measure(), unit='count')
    b = measure('80', ref='fixture:prior', period=PRIOR)
    assert compare_period(a, b, rule=period_rule(a, b)).reason == 'INVALID_MEASURE'


def test_interval_spanning_entire_guidance_cannot_be_classified_from_endpoints_alone():
    a = measure(None, support=Interval(D('80'), D('120'), False, False),
                support_basis='source_interval', support_ref='fixture:support')
    g = guidance('90', '110', lower_inclusive=False, upper_inclusive=False)
    out = compare_guidance(a, g, rule=guide_rule(a, g))
    assert (out.status, out.label, out.value) == ('QUALIFIED', 'ROUNDING_INDETERMINATE', None)


def test_nonpositive_prior_support_cannot_generate_underlying_percent_growth():
    a = measure('5')
    b = measure('1', ref='fixture:prior', period=PRIOR,
                support=Interval(D('0'), D('2'), True, True),
                support_basis='source_interval', support_ref='fixture:support')
    out = compare_period(a, b, rule=period_rule(a, b))
    assert (out.status, out.reason, out.value) == ('UNAVAILABLE', 'PRIOR_SUPPORT_NONPOSITIVE', None)


def test_owner_relation_does_not_turn_same_period_into_prior_growth():
    a, b = measure(), measure('80', ref='fixture:prior')
    assert compare_period(a, b, rule=period_rule(a, b)).reason == 'PERIOD_ORDER_INCOMPATIBLE'


def test_original_guidance_rule_preserves_reordered_binding_roles():
    a, g = measure('99'), guidance()
    r = guide_rule(a, g)
    assert compare_guidance(a, g, rule=replace(r, bindings=tuple(reversed(r.bindings)))) == compare_guidance(a, g, rule=r)


def test_finite_numeric_limits_refuse_oversized_coefficients():
    a = replace(measure(), value=D('9' * 49))
    b = measure('80', ref='fixture:prior', period=PRIOR)
    assert compare_period(a, b, rule=period_rule(a, b)).reason == 'INVALID_MEASURE'


def test_cash_repeated_receipt_cannot_supply_two_positive_economic_roles():
    a = measure('100')
    roles = (CashRole('first', 'first', 'signed_flow', 1),
             CashRole('second', 'second', 'signed_flow', 1))
    components = (CashComponent('first', a.ref, 'signed_flow', 1),
                  CashComponent('second', a.ref, 'signed_flow', 1))
    r = rule('cash', ('first', a), ('second', a), cash_roles=roles)
    out = cash_bridge(measures=(a,), components=components, rule=r)
    assert (out.status, out.reason, out.value) == ('INCOMPATIBLE', 'REPEATED_ECONOMIC_RECEIPT', None)


def test_nonoriginal_guidance_does_not_claim_original_vintage():
    a, g = measure(), guidance(vintage='latest_revision')
    out = compare_guidance(a, g, rule=guide_rule(a, g))
    assert (out.status, out.label, out.value) == ('QUALIFIED', 'GUIDANCE_VINTAGE_UNQUALIFIED', None)


def test_boolean_cash_coefficient_does_not_become_positive_one():
    values, components, r = cash_case()
    components = (replace(components[0], coefficient=True), components[1])
    out = cash_bridge(measures=values, components=components, rule=r)
    assert (out.status, out.reason, out.value) == ('INCOMPATIBLE', 'CASH_RECIPE_MISMATCH', None)


def test_support_and_scale_arithmetic_is_independent_of_caller_rounding_traps():
    from decimal import Inexact, Rounded, ROUND_DOWN
    a = measure('60801')
    b = measure('47516', ref='fixture:prior', period=PRIOR)
    r = period_rule(a, b)
    expected = compare_period(a, b, rule=r)
    with localcontext() as ctx:
        ctx.prec = 2
        ctx.rounding = ROUND_DOWN
        ctx.traps[Inexact] = True
        ctx.traps[Rounded] = True
        # localcontext copies pre-existing flags set by earlier test arithmetic.
        # Clear our own context first so this checks flags changed by the call.
        ctx.clear_flags()
        assert compare_period(a, b, rule=r) == expected
        assert ctx.prec == 2 and ctx.rounding == ROUND_DOWN
        assert not any(ctx.flags.values())


@pytest.mark.parametrize('ref', [[], {}, None])
def test_cash_rule_malformed_input_ref_never_reaches_hash_lookup(ref):
    values, components, r = cash_case()
    r = replace(r, bindings=(replace(r.bindings[0], ref=ref), r.bindings[1]))
    out = cash_bridge(measures=values, components=components, rule=r)
    assert out.status == 'INCOMPATIBLE'
    assert out.value is None
    assert out.reason == 'INPUT_BINDING_MISMATCH'
