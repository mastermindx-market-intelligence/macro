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


# AB01–AB08 are frozen DOCUMENTARY inputs with SYNTHETIC bindings. No native
# source/rights/review receipt, source precision or present-day coverage is implied.
from engine.market_ontology.communications_measures import (
    AccountingDependency, AccountingRule, AccountingTerm, accounting_bridge,
)

_ACCOUNTING_CASES = (
    ('AB01', 'meta', 'consolidated', 'operating_income', '1000000', PRIOR, '20441', '18775',
     (('revenue', '47516', '60801', 1), ('cost_of_revenue', '8491', '11330', -1),
      ('research_development', '12942', '21656', -1), ('marketing_sales', '2979', '3431', -1),
      ('general_admin', '2663', '5609', -1))),
    ('AB02', 'meta', 'consolidated', 'issuer_defined_fcf', '1000000', PRIOR, '8549', '784',
     (('operating_cash', '25561', '31862', 1), ('property_equipment', '16538', '30116', -1),
      ('lease_principal', '474', '962', -1))),
    ('AB03', 'alphabet', 'google_advertising', 'advertising_revenue', '1000000', PRIOR, '71340', '81629',
     (('search_other', '54190', '63271', 1), ('youtube_ads', '9796', '11055', 1),
      ('network', '7354', '7303', 1))),
    ('AB04', 'alphabet', 'consolidated', 'issuer_defined_fcf', '1000000', ('2026-01-01', '2026-03-31'), '10116', '-5855',
     (('operating_cash', '45790', '39069', 1), ('property_equipment', '35674', '44924', -1))),
    ('AB05', 'trade_desk', 'consolidated', 'operating_income', '1000', PRIOR, '116777', '101577',
     (('revenue', '694039', '715057', 1), ('platform_operations', '150980', '184333', -1),
      ('sales_marketing', '161131', '174404', -1), ('technology_development', '134251', '140742', -1),
      ('general_admin', '130900', '114001', -1))),
    ('AB06', 'magnite', 'consolidated', 'contribution_ex_tac', '1000', PRIOR, '161956', '189595',
     (('revenue', '173332', '192823', 1), ('derived_tac', '11376', '3228', -1))),
    ('AB07', 'magnite', 'consolidated', 'gross_profit', '1000', PRIOR, '108379', '130785',
     (('revenue', '173332', '192823', 1), ('cost_of_revenue', '64953', '62038', -1))),
    ('AB08', 'magnite', 'consolidated', 'contribution_ex_tac', '1000', PRIOR, '161956', '189595',
     (('ctv', '71543', '97133', 1), ('mobile', '63772', '65771', 1), ('desktop', '26641', '26691', 1))),
)


def accounting_case(index=0):
    case, issuer, scope, metric, scale, prior_period, before, after, rows = _ACCOUNTING_CASES[index]
    population = f'fixture:{issuer}:{scope}'
    def observation(value, name, period):
        return measure(value, ref=f'{population}:{name}:{period[0]}', metric=name,
                       definition_ref=f'fixture:def:{issuer}:{name}', population=population,
                       period=period, scale=D(scale), domain='signed_amount',
                       basis='issuer_defined' if name in ('issuer_defined_fcf', 'contribution_ex_tac') else 'reported_gaap',
                       support=None, support_basis='unknown')
    by_role = {'output_current': observation(after, metric, PERIOD),
               'output_prior': observation(before, metric, prior_period)}
    terms = []
    for name, old, new, coefficient in rows:
        current_role, prior_role = name + '_current', name + '_prior'
        by_role[current_role] = observation(new, name, PERIOD)
        by_role[prior_role] = observation(old, name, prior_period)
        terms.append(AccountingTerm(name, current_role, prior_role, coefficient,
                                    (f'fixture:coverage:{name}',)))
    dependencies = ()
    if case == 'AB06':
        dependencies = (AccountingDependency('derived_tac_current', ('revenue_current', 'output_current')),
                        AccountingDependency('derived_tac_prior', ('revenue_prior', 'output_prior')))
    comparison = rule('accounting', *by_role.items(), revision=f'fixture:accounting:{case}:v1',
                      interpretation_basis='published_figures')
    return tuple(by_role.values()), AccountingRule(comparison, tuple(terms), dependencies)


def accounting_rebind(recipe, observations, *, suffix=':rebound'):
    pairs = tuple((binding.role, observation) for binding, observation
                  in zip(recipe.comparison.bindings, observations))
    comparison = rule('accounting', *pairs, revision=recipe.comparison.revision + suffix,
                      interpretation_basis=recipe.comparison.interpretation_basis)
    return replace(recipe, comparison=comparison)


@pytest.mark.parametrize('index', range(8), ids=[row[0] for row in _ACCOUNTING_CASES])
def test_eight_accounting_bridges_use_product_comparator_and_keep_scope(index):
    observations, recipe = accounting_case(index)
    out = accounting_bridge(measures=observations, rule=recipe)
    assert (out.result.status, out.result.label, out.result.reason) == (
        'QUALIFIED', 'ACCOUNTING_RECONCILED', 'PUBLISHED_FIGURES_ONLY')
    assert out.reconstructed_current == observations[0].value
    assert out.residual == 0
    assert out.current_output == observations[0] and out.prior_output == observations[1]
    assert out.outcome_refs == (observations[0].ref, observations[1].ref)
    assert out.result.rule_revision == recipe.comparison.revision
    assert out.result.refs == tuple(m.ref for m in observations)
    assert tuple(p.component_key for p in out.contributions) == tuple(t.component_key for t in recipe.terms)
    assert sum(p.contribution for p in out.contributions) == observations[0].value - observations[1].value
    assert out.evidence_relation == ('TARGET_DEPENDENT' if index == 5 else 'INDEPENDENCE_UNASSESSED')
    assert 'cash' not in out.result.label.lower()


def test_sequential_consolidated_cash_keeps_negative_outcome_and_explicit_period():
    observations, recipe = accounting_case(3)
    out = accounting_bridge(measures=observations, rule=recipe)
    assert out.reconstructed_current == D('-5855')
    assert out.prior_output.period == ('2026-01-01', '2026-03-31')
    assert out.current_output.population == 'fixture:alphabet:consolidated'
    assert out.current_output.metric == 'issuer_defined_fcf'
    assert out.result.value == D('-5855')


@pytest.mark.parametrize('mutation', ['sign', 'component_value'])
def test_bad_accounting_equation_keeps_residual_without_fabricated_balancer(mutation):
    observations, recipe = accounting_case(0)
    if mutation == 'sign':
        recipe = replace(recipe, terms=(replace(recipe.terms[0], coefficient=-1),) + recipe.terms[1:])
    else:
        observations = observations[:2] + (replace(observations[2], value=observations[2].value + 10),) + observations[3:]
    out = accounting_bridge(measures=observations, rule=recipe)
    assert out.result.status == 'QUALIFIED' and out.result.label == 'ACCOUNTING_DISCREPANCY'
    assert out.residual != 0
    assert out.current_output.value == D('18775')
    assert len(out.contributions) == len(recipe.terms)
    assert all(part.component_key != 'residual' for part in out.contributions)


def test_corrected_magnite_total_exposes_channel_conflict_despite_dependent_cost_identity():
    cost_values, cost_rule = accounting_case(5)
    channel_values, channel_rule = accounting_case(7)
    def corrected(values, is_cost):
        result = list(values)
        result[0] = replace(result[0], ref=result[0].ref + ':corrected', value=D('190595'))
        if is_cost:
            result[4] = replace(result[4], ref=result[4].ref + ':corrected', value=D('2228'))
        return tuple(result)
    cost_values = corrected(cost_values, True)
    channel_values = corrected(channel_values, False)
    stale = accounting_bridge(measures=cost_values, rule=cost_rule)
    assert stale.result.reason == 'INPUT_BINDING_MISMATCH' and stale.reconstructed_current is None
    cost = accounting_bridge(measures=cost_values, rule=accounting_rebind(cost_rule, cost_values))
    channel = accounting_bridge(measures=channel_values, rule=accounting_rebind(channel_rule, channel_values))
    assert cost.residual == 0 and cost.evidence_relation == 'TARGET_DEPENDENT'
    assert channel.residual == D('1000') and channel.reconstructed_current == D('189595')
    assert channel.result.label == 'ACCOUNTING_DISCREPANCY'
    assert cost.outcome_refs == channel.outcome_refs
    assert cost.current_output.value == channel.current_output.value == D('190595')
    assert tuple(p.contribution for p in channel.contributions) == (D('25590'), D('1999'), D('50'))
    assert 'independent' not in cost.result.label.lower()


def test_alternative_accounting_views_share_one_outcome_not_two_improvements():
    a, ar = accounting_case(5)
    b, br = accounting_case(7)
    cost, channels = accounting_bridge(measures=a, rule=ar), accounting_bridge(measures=b, rule=br)
    assert cost.outcome_refs == channels.outcome_refs
    assert cost.result.rule_revision != channels.result.rule_revision
    assert cost.current_output.value - cost.prior_output.value == D('27639')
    assert channels.current_output.value - channels.prior_output.value == D('27639')
    assert cost.evidence_relation == 'TARGET_DEPENDENT'
    assert channels.evidence_relation == 'INDEPENDENCE_UNASSESSED'


@pytest.mark.parametrize('field,changed', [('period', PRIOR), ('population', 'fixture:alphabet:search_only'),
                                          ('currency', 'EUR'), ('metric', 'other_metric')])
def test_rebound_accounting_input_still_cannot_cross_scope_or_period(field, changed):
    observations, recipe = accounting_case(3)
    observations = observations[:2] + (replace(observations[2], **{field: changed}),) + observations[3:]
    out = accounting_bridge(measures=observations, rule=accounting_rebind(recipe, observations))
    assert out.result.status == 'INCOMPATIBLE' and out.result.reason == 'ACCOUNTING_SCOPE_MISMATCH'
    assert out.residual is None


def test_accounting_scaling_converts_whole_equation_and_preserves_source_objects():
    observations, recipe = accounting_case(2)
    changed = list(observations)
    changed[2] = replace(changed[2], value=changed[2].value * 1000, scale=changed[2].scale / 1000)
    changed = tuple(changed)
    out = accounting_bridge(measures=changed, rule=accounting_rebind(recipe, changed))
    assert out.residual == 0 and out.reconstructed_current == D('81629')
    assert out.current_output.scale == D('1000000')
    assert out.contributions[0].contribution == D('9081')
    assert observations[2].value == D('63271')


@pytest.mark.parametrize('missing', ['component', 'current_value', 'current_output'])
def test_missing_accounting_input_never_becomes_zero(missing):
    observations, recipe = accounting_case(1)
    if missing == 'component':
        observations = observations[:-1]
    else:
        position = 0 if missing == 'current_output' else 2
        observations = tuple(replace(m, value=None) if i == position else m for i, m in enumerate(observations))
    out = accounting_bridge(measures=observations, rule=recipe)
    assert out.result.status == ('INCOMPATIBLE' if missing == 'component' else 'UNAVAILABLE')
    assert out.result.reason == ('INPUT_BINDING_MISMATCH' if missing == 'component' else 'POINT_VALUE_UNAVAILABLE')
    assert out.reconstructed_current is None and out.residual is None


def test_overlapping_net_subtotal_and_components_refuse_even_with_fitting_arithmetic():
    observations, recipe = accounting_case(0)
    terms = (replace(recipe.terms[0], covered_components=('fixture:net:costs', 'fixture:coverage:cost_of_revenue')),) + recipe.terms[1:]
    out = accounting_bridge(measures=observations, rule=replace(recipe, terms=terms))
    assert out.result.reason == 'ACCOUNTING_COMPONENT_OVERLAP'
    assert out.result.status == 'INCOMPATIBLE'


@pytest.mark.parametrize('bad', [True, 0, 2, -2, [], None])
def test_accounting_coefficient_has_closed_integer_sign_domain(bad):
    observations, recipe = accounting_case()
    recipe = replace(recipe, terms=(replace(recipe.terms[0], coefficient=bad),) + recipe.terms[1:])
    out = accounting_bridge(measures=observations, rule=recipe)
    assert out.result.reason == 'INVALID_ACCOUNTING_RECIPE'


@pytest.mark.parametrize('dependencies', [
    (AccountingDependency('missing', ('output_current',)),),
    (AccountingDependency('revenue_current', ('missing',)),),
    (AccountingDependency('revenue_current', ('revenue_current',)),),
    (AccountingDependency('revenue_current', ('cost_of_revenue_current',)),
     AccountingDependency('cost_of_revenue_current', ('revenue_current',))),
])
def test_unknown_or_cyclic_accounting_dependence_is_not_silently_ignored(dependencies):
    observations, recipe = accounting_case()
    out = accounting_bridge(measures=observations, rule=replace(recipe, dependencies=dependencies))
    assert out.result.status == 'INCOMPATIBLE' and out.result.reason == 'ACCOUNTING_DEPENDENCY_MISMATCH'


def test_accounting_results_do_not_depend_on_caller_decimal_context_or_input_order():
    observations, recipe = accounting_case(0)
    expected = accounting_bridge(measures=observations, rule=recipe)
    assert expected.result.label == 'ACCOUNTING_RECONCILED'
    with localcontext() as context:
        context.prec = 2
        context.clear_flags()
        assert accounting_bridge(measures=tuple(reversed(observations)), rule=recipe) == expected
        assert not any(context.flags.values())
    with pytest.raises(FrozenInstanceError):
        expected.residual = D('99')


def test_accounting_derivation_cannot_bind_current_component_to_prior_period_total():
    observations, recipe = accounting_case(5)
    wrong = (AccountingDependency('derived_tac_current', ('revenue_current', 'output_prior')),)
    out = accounting_bridge(measures=observations, rule=replace(recipe, dependencies=wrong))
    assert out.result.reason == 'ACCOUNTING_DEPENDENCY_MISMATCH'
    assert out.reconstructed_current is None


@pytest.mark.parametrize('index,position,mutation', [
    (i, j, mutation) for i, case in enumerate(_ACCOUNTING_CASES)
    for j in range(len(case[-1])) for mutation in ('sign', 'omitted', 'scale', 'duplicated')
])
def test_frozen_accounting_hostile_inputs_reach_real_product_refusal(index, position, mutation):
    # These are 100 input perturbations, NOT a production-code mutation score.
    observations, recipe = accounting_case(index)
    current_position, prior_position = 2 + 2 * position, 3 + 2 * position
    if mutation == 'sign':
        terms = list(recipe.terms)
        terms[position] = replace(terms[position], coefficient=-terms[position].coefficient)
        recipe = replace(recipe, terms=tuple(terms))
    elif mutation == 'omitted':
        observations = tuple(m for i, m in enumerate(observations) if i not in (current_position, prior_position))
    elif mutation == 'scale':
        observations = tuple(replace(m, scale=m.scale * 1000) if i in (current_position, prior_position) else m
                             for i, m in enumerate(observations))
        recipe = accounting_rebind(recipe, observations)
    else:
        recipe = replace(recipe, terms=recipe.terms + (recipe.terms[position],))
    out = accounting_bridge(measures=observations, rule=recipe)
    assert out.result.label != 'ACCOUNTING_RECONCILED'
    if mutation in ('sign', 'scale'):
        assert out.result.label == 'ACCOUNTING_DISCREPANCY' and out.residual != 0
    else:
        assert out.result.status == 'INCOMPATIBLE' and out.reconstructed_current is None


@pytest.mark.parametrize('target,bad', [
    ('terms', None), ('terms', []), ('terms', ()), ('terms', ({},)),
    ('dependencies', None), ('dependencies', []), ('dependencies', ({},)),
])
def test_malformed_accounting_containers_return_typed_refusal(target, bad):
    observations, recipe = accounting_case()
    out = accounting_bridge(measures=observations, rule=replace(recipe, **{target: bad}))
    assert out.result.status == 'INCOMPATIBLE' and out.reconstructed_current is None
    assert out.result.reason == ('INVALID_ACCOUNTING_RECIPE' if target == 'terms' else 'ACCOUNTING_DEPENDENCY_MISMATCH')


@pytest.mark.parametrize('field,bad', [('component_key', []), ('current_role', {}),
                                     ('prior_role', None), ('covered_components', 'revenue'),
                                     ('covered_components', ([],)), ('covered_components', ())])
def test_malformed_accounting_term_returns_typed_refusal(field, bad):
    observations, recipe = accounting_case()
    changed = replace(recipe.terms[0], **{field: bad})
    out = accounting_bridge(measures=observations, rule=replace(recipe, terms=(changed,) + recipe.terms[1:]))
    assert out.result.reason == 'INVALID_ACCOUNTING_RECIPE' and out.residual is None


def test_exact_synthetic_accounting_stays_distinct_from_unknown_source_precision():
    observations, recipe = accounting_case(0)
    exact = tuple(replace(m, support=Interval(m.value, m.value, True, True), support_basis='exact') for m in observations)
    exact_rule = replace(recipe, comparison=replace(recipe.comparison, interpretation_basis='underlying_interval'))
    out = accounting_bridge(measures=exact, rule=exact_rule)
    assert (out.result.status, out.result.reason) == ('COMPARABLE', None)
    unknown = accounting_bridge(measures=observations, rule=exact_rule)
    assert (unknown.result.status, unknown.result.reason) == ('QUALIFIED', 'PUBLISHED_FIGURES_ONLY')
    assert out.evidence_relation == unknown.evidence_relation == 'INDEPENDENCE_UNASSESSED'
