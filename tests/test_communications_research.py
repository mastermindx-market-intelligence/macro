"""Task4A internal claim projection. ALL input/review/identity refs are synthetic.

No native reader, rights decision, shared wire protocol, UI or release is proven.
Frozen documentary numbers are regression examples, not current source admission.
"""
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal as D, localcontext

import pytest

from engine.market_ontology.communications_measures import (
    AccountingDependency, AccountingRule, AccountingTerm, ComparisonRule,
    Guidance, InputBinding, Interval, Measure,
)
from engine.market_ontology.communications_research import (
    ClaimInputError, CompanyClaimInput, PairSelection, compose_four_company_claims,
)

CURRENT = ('2026-04-01', '2026-06-30')
PRIOR = ('2025-04-01', '2025-06-30')
ROSTER = ('meta', 'alphabet', 'trade_desk', 'magnite')
EXAMPLES = {
    'meta': (('revenue', '60801', '47516'), ('operating_income', '18775', '20441')),
    'alphabet': (('search_other_revenue', '63271', '54190'), ('network_revenue', '7303', '7354')),
    'trade_desk': (('revenue', '715057', '694039'), ('operating_income', '101577', '116777')),
    'magnite': (('contribution_ex_tac', '189595', '161956'), ('gross_profit', '130785', '108379')),
}


def fact(slot, metric, value, *, prior=False, ref=None):
    return Measure(
        ref or f'fixture:{slot}:{metric}:{"prior" if prior else "current"}',
        metric, f'fixture:{slot}:issuer', PRIOR if prior else CURRENT,
        'USD', D('1000000' if slot in ('meta', 'alphabet') else '1000'),
        'issuer_defined' if metric == 'contribution_ex_tac' else 'reported_gaap',
        D(value), 'signed_amount' if metric == 'operating_income' else 'nonnegative_amount',
        f'fixture:definition:{metric}', 'currency', None, 'unknown', None,
    )


def rule(operation, *roles, revision='fixture:rule'):
    return ComparisonRule(
        revision, operation,
        tuple(InputBinding(role, m.ref, m.definition_ref, m.population, m.period,
                           m.unit, m.currency, m.scale, getattr(m, 'domain', 'nonnegative_amount'))
              for role, m in roles),
        'fixture:relation', 'fixture:review', 'published_figures', (),
    )


def company(slot='meta'):
    facts, pairs = [], []
    for metric, current, prior in EXAMPLES[slot]:
        a, b = fact(slot, metric, current), fact(slot, metric, prior, prior=True)
        facts.extend((a, b))
        pairs.append(PairSelection(a.ref, b.ref,
            rule('period_pct', ('current', a), ('prior', b), revision=f'fixture:{slot}:{metric}:growth-rule')))
    guide = guide_rule = None
    if slot != 'alphabet':
        lo, hi = {'meta': ('58000', '61000'), 'trade_desk': ('750', None), 'magnite': ('175', '181')}[slot]
        a = facts[0]
        guide = Guidance(f'fixture:{slot}:guide', a.metric, a.population, CURRENT, 'USD', D('1000000'),
                         a.basis, D(lo), None if hi is None else D(hi), True, None if hi is None else True,
                         '2026-04-29', 'original_company_guidance', a.definition_ref, 'currency', 'stated_threshold')
        guide_rule = rule('guidance', ('actual', a), ('guide', guide), revision=f'fixture:{slot}:guide-rule')
    return CompanyClaimInput(slot, tuple(facts), tuple(pairs), guide, guide_rule)


def panel(value, slot='meta'):
    return next(p for p in value.panels if p.slot == slot)


def replace_record(item, position, **changes):
    records = list(item.measures)
    records[position] = replace(records[position], **changes)
    return replace(item, measures=tuple(records))


def accounting_magnite():
    item = company('magnite')
    a, b = item.measures[:2]
    records = list(item.measures)
    recipes = []
    for name, terms in (
        ('cost', (('revenue', '192823', '173332', 1), ('derived_tac', '3228', '11376', -1))),
        ('channels', (('ctv', '97133', '71543', 1), ('mobile', '65771', '63772', 1), ('desktop', '26691', '26641', 1))),
    ):
        roles = [('output_current', a), ('output_prior', b)]
        rules = []
        for key, current, prior, coefficient in terms:
            x, y = fact('magnite', key, current), fact('magnite', key, prior, prior=True)
            records.extend((x, y))
            roles.extend(((key + '_current', x), (key + '_prior', y)))
            rules.append(AccountingTerm(key, key + '_current', key + '_prior', coefficient, ('fixture:coverage:' + key,)))
        deps = (AccountingDependency('derived_tac_current', ('revenue_current', 'output_current')),
                AccountingDependency('derived_tac_prior', ('revenue_prior', 'output_prior'))) if name == 'cost' else ()
        recipes.append(AccountingRule(rule('accounting', *roles, revision=f'fixture:magnite:{name}:rule'), tuple(rules), deps))
    return replace(item, measures=tuple(records), accounting_rules=tuple(recipes))


def test_four_fixed_panels_lead_with_reported_changes_not_trade_rank():
    result = compose_four_company_claims(tuple(company(s) for s in ROSTER))
    assert tuple(p.slot for p in result.panels) == ROSTER
    assert result.expected_issuer_count == result.headline_issuer_count == 4
    assert panel(result).headline.en == 'Reported revenue increased; reported operating income decreased.'
    assert panel(result, 'alphabet').headline.en == 'Reported Search & other revenue increased; reported Network revenue decreased.'
    assert panel(result, 'magnite').headline.en == 'Reported contribution ex-TAC increased; reported gross profit increased.'
    assert panel(result, 'alphabet').guidance is None
    assert panel(result, 'trade_desk').guidance.label == 'BELOW_ORIGINAL_FLOOR'
    assert panel(result, 'magnite').guidance.label == 'ABOVE_ORIGINAL_CEILING'
    assert result.limitations == ('native_source_mapping_unbound', 'shared_delivery_unbound', 'source_completeness_unqualified')
    assert not any(vars(result.authority).values())


@pytest.mark.parametrize('missing', ROSTER)
def test_missing_company_stays_in_denominator_and_does_not_create_a_route(missing):
    result = compose_four_company_claims(tuple(company(s) for s in ROSTER if s != missing))
    assert len(result.panels) == result.expected_issuer_count == 4
    assert result.headline_issuer_count == 3
    absent = panel(result, missing)
    assert absent.headline is None and len(absent.measures) == 2
    assert all(r.current is None and r.trend is None for r in absent.measures)
    assert not hasattr(absent, 'company_route')


def test_missing_prior_removes_only_dependent_growth_and_headline():
    item = company()
    item = replace(item, measures=tuple(m for m in item.measures if m.ref != item.pairs[0].prior_ref))
    out = panel(compose_four_company_claims((item,)))
    assert out.measures[0].current.value == D('60801')
    assert out.measures[0].comparison is None and out.measures[0].trend is None
    assert out.measures[1].trend is not None
    assert out.headline is None
    assert out.guidance.label == 'WITHIN_ORIGINAL_RANGE'


def test_missing_current_never_echoes_its_ref_via_stale_guidance_or_prose():
    item = company()
    missing = item.pairs[0].current_ref
    item = replace(item, measures=tuple(m for m in item.measures if m.ref != missing))
    out = panel(compose_four_company_claims((item,)))
    assert out.measures[0].current is None and out.headline is None and out.guidance is None
    assert missing not in repr(out)
    assert out.measures[1].current is not None


def test_correction_keeps_new_level_but_requires_exact_rule_rebinding():
    old = company()
    new = replace_record(old, 0, ref=old.measures[0].ref + ':corrected', value=D('50000'))
    new = replace(new, pairs=(replace(new.pairs[0], current_ref=new.measures[0].ref), new.pairs[1]))
    out = panel(compose_four_company_claims((new,)))
    assert out.measures[0].current.value == D('50000')
    assert out.measures[0].comparison.reason == 'INPUT_BINDING_MISMATCH'
    assert out.measures[0].trend is None and out.headline is None
    assert out.guidance is None
    assert out.measures[1].trend is not None


def test_same_immutable_observation_ref_with_different_bytes_refuses_mixed_snapshot():
    item = company()
    with pytest.raises(ClaimInputError, match='INPUT_REVISION_CONFLICT'):
        compose_four_company_claims((replace(item, measures=item.measures + (replace(item.measures[0], value=D('1')),)),))


def test_missing_original_guidance_does_not_remove_operating_analysis():
    item = company()
    out = panel(compose_four_company_claims((replace(item, guide=None),)))
    assert out.headline is not None and out.guidance is None
    assert all(r.trend is not None for r in out.measures)
    assert not hasattr(out, 'consensus')


def test_source_rights_withholding_is_input_omission_not_a_domain_rights_engine():
    item = company()
    removed = {item.pairs[0].current_ref, item.pairs[0].prior_ref}
    out = panel(compose_four_company_claims((replace(item, measures=tuple(m for m in item.measures if m.ref not in removed)),)))
    assert all(ref not in repr(out) for ref in removed)
    assert out.headline is None and out.guidance is None
    assert out.measures[1].trend is not None


def test_unused_permitted_observations_do_not_change_visible_output_or_coverage():
    item = company()
    unused = fact('meta', 'unused_metric', '123')
    expected = compose_four_company_claims((item,))
    assert expected.headline_issuer_count == 1
    assert compose_four_company_claims((replace(item, measures=item.measures + (unused,)),)) == expected


@pytest.mark.parametrize('changes', [{'metric':'costs'}, {'currency':'EUR'}, {'unit':'count'}, {'value':D('NaN')}])
def test_invalid_or_wrong_role_observation_cannot_be_labeled_revenue(changes):
    item = replace_record(company(), 0, **changes)
    out = panel(compose_four_company_claims((item,)))
    assert out.measures[0].current is None and out.headline is None
    assert out.measures[1].trend is not None


def test_mixed_pair_reporting_periods_keep_individual_trends_not_combined_headline():
    item = company()
    records = list(item.measures)
    records[2] = replace(records[2], period=('2026-01-01','2026-03-31'))
    p = item.pairs[1]
    p = replace(p, rule=rule('period_pct', ('current', records[2]), ('prior', records[3]), revision='fixture:mixed-period-rule'))
    out = panel(compose_four_company_claims((replace(item, measures=tuple(records), pairs=(item.pairs[0],p)),)))
    assert all(r.trend is not None for r in out.measures)
    assert out.headline is None


def test_supported_declines_are_descriptive_not_missing_or_a_sell_signal():
    item = company()
    records = tuple(replace(m, value=m.value / 2) if i % 2 == 0 else m for i,m in enumerate(item.measures))
    # Fixture-only new values; rebuild refs/rules to represent new immutable observations.
    records = tuple(replace(m, ref=m.ref + ':decline') for m in records)
    pairs = tuple(PairSelection(records[i].ref, records[i+1].ref,
                  rule('period_pct', ('current', records[i]), ('prior', records[i+1]), revision=f'fixture:decline:{i}')) for i in (0,2))
    result = compose_four_company_claims((replace(item, measures=records, pairs=pairs, guide=None),))
    assert result.headline_issuer_count == 1
    assert panel(result).headline.en.count('decreased') == 2
    assert not any(vars(result.authority).values())


def test_current_interval_without_point_remains_visible_without_fabricated_growth():
    item = replace_record(company(), 0, value=None, support=Interval(D('60000'),D('61000'),True,True), support_basis='source_interval', support_ref='fixture:interval')
    out = panel(compose_four_company_claims((item,)))
    assert out.measures[0].current.support.lower == D('60000')
    assert out.measures[0].trend is None and out.headline is None


def test_alternative_accounting_views_form_one_group_without_summed_improvement():
    out = panel(compose_four_company_claims((accounting_magnite(),)), 'magnite')
    assert len(out.accounting) == 1 and len(out.accounting[0].views) == 2
    group = out.accounting[0]
    assert all(v.outcome_refs == group.outcome_refs for v in group.views)
    assert {v.evidence_relation for v in group.views} == {'TARGET_DEPENDENT','INDEPENDENCE_UNASSESSED'}
    assert not hasattr(group, 'summed_improvement') and not hasattr(group, 'confidence')


def test_missing_accounting_operand_removes_only_affected_view():
    item = accounting_magnite()
    item = replace(item, measures=tuple(m for m in item.measures if m.metric != 'ctv'))
    out = panel(compose_four_company_claims((item,)), 'magnite')
    assert out.headline is not None
    assert len(out.accounting) == 1 and len(out.accounting[0].views) == 1
    assert out.accounting[0].views[0].evidence_relation == 'TARGET_DEPENDENT'
    assert 'fixture:magnite:ctv' not in repr(out)


def test_stale_accounting_total_cannot_survive_new_headline_selection():
    item = accounting_magnite()
    new = replace(item.measures[0], ref='fixture:magnite:contribution:new', value=D('190595'))
    item = replace(item, measures=item.measures + (new,), pairs=(replace(item.pairs[0],current_ref=new.ref),item.pairs[1]))
    out = panel(compose_four_company_claims((item,)), 'magnite')
    assert out.measures[0].current == new and out.headline is None
    assert out.accounting == ()


def test_bilingual_claims_are_bounded_and_carry_only_available_support_and_rules():
    for slot in ROSTER:
        item = company(slot)
        out = panel(compose_four_company_claims((item,)), slot)
        available = {m.ref for m in item.measures}
        for claim in (out.headline, *(r.trend for r in out.measures)):
            assert claim is not None
            assert 0 < len(claim.en) <= 240 and 0 < len(claim.zh) <= 240
            assert set(claim.refs) <= available
            assert claim.rule_revisions and claim.interpretation_basis == 'published_figures'
        assert out.next_observation_en and out.next_observation_zh


def test_input_order_and_decimal_context_do_not_change_projection():
    items = tuple(company(s) for s in ROSTER)
    expected = compose_four_company_claims(items)
    assert expected.headline_issuer_count == 4
    permuted = tuple(replace(i,measures=tuple(reversed(i.measures))) for i in reversed(items))
    with localcontext() as context:
        context.prec = 2
        context.clear_flags()
        assert compose_four_company_claims(permuted) == expected
        assert not any(context.flags.values())
    with pytest.raises(FrozenInstanceError):
        expected.headline_issuer_count = 99


@pytest.mark.parametrize('value', [None, [], {}, 'meta', (None,), ({} ,)])
def test_malformed_outer_input_refuses_with_fixed_non_echoing_error(value):
    with pytest.raises(ClaimInputError, match='INVALID_CLAIM_INPUT'):
        compose_four_company_claims(value)


@pytest.mark.parametrize('slot', ['unknown', 'META', '<script>private</script>', [], None])
def test_unknown_or_malformed_roster_slot_is_not_a_new_company(slot):
    with pytest.raises(ClaimInputError, match='INVALID_CLAIM_INPUT') as error:
        compose_four_company_claims((replace(company(),slot=slot),))
    assert 'script' not in str(error.value)


def test_duplicate_issuer_is_refused_instead_of_counted_twice():
    with pytest.raises(ClaimInputError, match='DUPLICATE_ISSUER'):
        compose_four_company_claims((company(), company()))


def test_cardinality_limits_refuse_without_truncating_records():
    item = company()
    extras = tuple(fact('meta','unused','1',ref=f'fixture:extra:{i}') for i in range(97))
    with pytest.raises(ClaimInputError, match='CLAIM_INPUT_LIMIT'):
        compose_four_company_claims((replace(item,measures=extras),))


def test_conflicting_review_revision_cannot_be_reused_for_different_rules():
    item = company()
    changed = replace(item.pairs[1],rule=replace(item.pairs[1].rule,revision=item.pairs[0].rule.revision))
    with pytest.raises(ClaimInputError, match='RULE_REVISION_CONFLICT'):
        compose_four_company_claims((replace(item,pairs=(item.pairs[0],changed)),))


@pytest.mark.parametrize('slot', ('meta','trade_desk','magnite'))
def test_guidance_output_retains_original_bounds_units_publication_and_vintage(slot):
    item = company(slot)
    out = panel(compose_four_company_claims((item,)), slot)
    assert getattr(out, 'original_guidance', None) == item.guide
    assert out.guidance.refs == (item.measures[0].ref, item.guide.ref)


@pytest.mark.parametrize('slot', ROSTER)
def test_company_specific_caveats_remain_bounded_bilingual_and_non_actionable(slot):
    out = panel(compose_four_company_claims((company(slot),)), slot)
    assert 0 < len(getattr(out, 'limitation_en', '')) <= 240
    assert 0 < len(getattr(out, 'limitation_zh', '')) <= 240


def test_missing_guide_does_not_retain_original_bounds_in_a_second_output_field():
    item = company()
    before = panel(compose_four_company_claims((item,)))
    assert getattr(before, 'original_guidance', None) == item.guide
    after = panel(compose_four_company_claims((replace(item, guide=None),)))
    assert after.guidance is None and after.original_guidance is None
    assert item.guide.ref not in repr(after)


def test_corrected_accounting_discrepancy_survives_projection_without_stale_headline():
    item = accounting_magnite()
    replacements = {}
    for m in item.measures:
        if m.metric == 'contribution_ex_tac' and m.period == CURRENT:
            replacements[m.ref] = replace(m, ref=m.ref + ':corrected', value=D('190595'))
        if m.metric == 'derived_tac' and m.period == CURRENT:
            replacements[m.ref] = replace(m, ref=m.ref + ':corrected', value=D('2228'))
    records = tuple(replacements.get(m.ref,m) for m in item.measures)
    recipes = []
    for recipe in item.accounting_rules:
        bindings = tuple(replace(b, ref=replacements[b.ref].ref) if b.ref in replacements else b for b in recipe.comparison.bindings)
        recipes.append(replace(recipe, comparison=replace(recipe.comparison, bindings=bindings, revision=recipe.comparison.revision+':corrected')))
    current_ref = replacements[item.pairs[0].current_ref].ref
    item = replace(item, measures=records, pairs=(replace(item.pairs[0], current_ref=current_ref),item.pairs[1]), accounting_rules=tuple(recipes))
    out = panel(compose_four_company_claims((item,)), 'magnite')
    assert out.headline is None and out.measures[0].current.value == D('190595')
    assert len(out.accounting) == 1 and len(out.accounting[0].views) == 2
    assert {v.residual for v in out.accounting[0].views} == {D('0'),D('1000')}
    assert all(v.current_output.value == D('190595') for v in out.accounting[0].views)


def test_absolute_loss_change_retains_supported_direction_without_fake_percentage():
    item = company()
    a = replace(item.measures[2], value=D('-10'), ref='fixture:loss:current')
    b = replace(item.measures[3], value=D('-20'), ref='fixture:loss:prior')
    pair = PairSelection(a.ref, b.ref, rule('period_absolute', ('current',a), ('prior',b), revision='fixture:loss:rule'))
    item = replace(item, measures=item.measures[:2]+(a,b), pairs=(item.pairs[0],pair))
    out = panel(compose_four_company_claims((item,)))
    assert out.measures[1].comparison.label == 'ABSOLUTE_CHANGE'
    assert out.measures[1].comparison.value == D('10000000')
    assert out.measures[1].trend.en == 'Reported operating income increased.'
    assert out.headline is not None


@pytest.mark.parametrize('changes', [{'pairs':[]}, {'pairs':(None,None)}, {'measures':[None]}, {'accounting_rules':[]}, {'guide':{} }])
def test_malformed_inner_shapes_have_no_untyped_exceptions(changes):
    with pytest.raises(ClaimInputError, match='INVALID_CLAIM_INPUT'):
        compose_four_company_claims((replace(company(), **changes),))


def test_oversized_rule_binding_sequence_is_rejected_before_any_comparison():
    item = company()
    oversized = replace(item.pairs[0].rule, bindings=item.pairs[0].rule.bindings * 100)
    pair = replace(item.pairs[0], rule=oversized)
    with pytest.raises(ClaimInputError, match='CLAIM_INPUT_LIMIT'):
        compose_four_company_claims((replace(item,pairs=(pair,item.pairs[1])),))


def test_exact_same_observation_cannot_count_for_two_roster_issuers():
    meta, alphabet = company(), company('alphabet')
    alphabet = replace(alphabet, measures=alphabet.measures+(meta.measures[0],))
    with pytest.raises(ClaimInputError, match='CROSS_ISSUER_INPUT_REUSE'):
        compose_four_company_claims((meta,alphabet))


def test_identical_duplicate_accounting_view_is_not_extra_corroboration():
    item = accounting_magnite()
    expected = compose_four_company_claims((item,))
    duplicated = replace(item, accounting_rules=item.accounting_rules+(item.accounting_rules[0],))
    assert len(panel(expected,'magnite').accounting[0].views) == 2
    assert compose_four_company_claims((duplicated,)) == expected


@pytest.mark.parametrize('vintage', ['final_pre_result_guidance', 'analyst_consensus'])
def test_nonoriginal_outlook_cannot_occupy_original_company_guidance_fields(vintage):
    item = company()
    item = replace(item, guide=replace(item.guide, vintage=vintage))
    out = panel(compose_four_company_claims((item,)))
    assert out.headline is not None
    assert out.guidance is None and out.original_guidance is None


def test_retained_original_guidance_disappears_after_actual_rule_is_invalidated():
    item = company()
    item = replace(item, guide_rule=replace(item.guide_rule, review_ref=''))
    out = panel(compose_four_company_claims((item,)))
    assert out.headline is not None
    assert out.guidance is None and out.original_guidance is None


# Task4B domain-payload candidate: no native or shared registration is claimed.
from copy import deepcopy
import json
from pathlib import Path
from engine.market_ontology import communications_research as cr


def payload_example():
    return cr.compose_communications_payload(tuple(company(s) for s in ROSTER))


def test_domain_payload_has_four_slots_and_cannot_claim_native_binding():
    payload = payload_example()
    assert set(payload) == {'schema', 'binding_state', 'projection'}
    assert payload['schema'] == 'communications_business_research.v1'
    assert payload['binding_state'] == 'unbound'
    assert [p['slot'] for p in payload['projection']['panels']] == list(ROSTER)
    assert payload['projection']['headline_issuer_count'] == 4
    assert payload['projection']['expected_issuer_count'] == 4
    assert cr.validate_view(payload) is None
    assert 'generation' not in payload and 'request' not in payload
    assert not any(payload['projection']['authority'].values())


def test_payload_preserves_decimal_value_scale_and_unknown_precision_losslessly():
    item = replace_record(company(), 0, value=D('9007199254740993.0000001'))
    payload = cr.compose_communications_payload((item,))
    measure = payload['projection']['panels'][0]['measures'][0]['current']
    assert measure['value'] == '9007199254740993.0000001'
    assert measure['scale'] == '1000000'
    assert measure['support'] is None and measure['support_basis'] == 'unknown'
    encoded = cr.encode_communications_payload((item,))
    assert type(encoded) is bytes
    assert json.loads(encoded) == payload
    assert b'9007199254740993.0000001' in encoded


def test_payload_keeps_current_level_but_not_unsupported_growth():
    item = company()
    missing = item.pairs[0].prior_ref
    item = replace(item, measures=tuple(m for m in item.measures if m.ref != missing))
    payload = cr.compose_communications_payload((item,))
    row = payload['projection']['panels'][0]['measures'][0]
    assert row['current']['value'] == '60801'
    assert row['prior'] is None and row['comparison'] is None and row['trend'] is None
    assert payload['projection']['panels'][0]['headline'] is None
    assert missing not in json.dumps(payload)


def test_payload_preserves_original_guidance_without_unit_or_vintage_relabeling():
    payload = payload_example()
    panel = payload['projection']['panels'][2]
    guide = panel['original_guidance']
    assert guide['lower'] == '750' and guide['scale'] == '1000000'
    assert guide['upper'] is None and guide['upper_inclusive'] is None
    assert guide['published'] == company('trade_desk').guide.published
    assert guide['period'] == list(CURRENT)
    assert guide['vintage'] == 'original_company_guidance'
    assert panel['guidance']['label'] == 'BELOW_ORIGINAL_FLOOR'
    assert payload['projection']['panels'][1]['original_guidance'] is None


def test_payload_groups_accounting_alternatives_without_summing_them():
    payload = cr.compose_communications_payload((accounting_magnite(),))
    groups = payload['projection']['panels'][3]['accounting']
    assert len(groups) == 1 and len(groups[0]['views']) == 2
    assert {v['residual'] for v in groups[0]['views']} == {'0'}
    assert {v['evidence_relation'] for v in groups[0]['views']} == {'TARGET_DEPENDENT', 'INDEPENDENCE_UNASSESSED'}
    for view in groups[0]['views']:
        assert [view['current_output']['ref'], view['prior_output']['ref']] == groups[0]['outcome_refs']
    assert 'total_improvement' not in groups[0]
    assert cr.validate_view(payload) is None


@pytest.mark.parametrize('bad', [True, 1, 'false', None])
def test_payload_authority_is_literal_false_not_falsy_or_truthy(bad):
    payload = payload_example()
    payload['projection']['authority']['can_rank'] = bad
    with pytest.raises(ClaimInputError, match='^INVALID_CLAIM_VIEW$'):
        cr.validate_view(payload)


@pytest.mark.parametrize('bad', [60801, 1.5, True, 'NaN', 'Infinity', '1e20', '0' * 400])
def test_payload_numeric_fields_refuse_nondecimal_or_unbounded_forms(bad):
    payload = payload_example()
    payload['projection']['panels'][0]['measures'][0]['current']['value'] = bad
    with pytest.raises(ClaimInputError, match='^INVALID_CLAIM_VIEW$'):
        cr.validate_view(payload)


@pytest.mark.parametrize('where', ['root', 'panel', 'measurement', 'authority'])
def test_payload_is_closed_and_errors_never_echo_private_values(where):
    payload = payload_example()
    targets = {'root': payload, 'panel': payload['projection']['panels'][0],
               'measurement': payload['projection']['panels'][0]['measures'][0]['current'],
               'authority': payload['projection']['authority']}
    targets[where]['unknown'] = 'PRIVATE_PAYLOAD_CANARY'
    with pytest.raises(ClaimInputError) as error:
        cr.validate_view(payload)
    assert str(error.value) == 'INVALID_CLAIM_VIEW'
    assert 'PRIVATE_PAYLOAD_CANARY' not in str(error.value)


@pytest.mark.parametrize('mutation', ['count', 'order', 'duplicate', 'missing', 'binding', 'claim_ref', 'outcome_ref'])
def test_payload_rejects_internally_inconsistent_coverage_and_lineage(mutation):
    payload = cr.compose_communications_payload((company(), accounting_magnite()))
    projection = payload['projection']
    if mutation == 'count': projection['headline_issuer_count'] = 4
    elif mutation == 'order': projection['panels'].reverse()
    elif mutation == 'duplicate': projection['panels'][1] = deepcopy(projection['panels'][0])
    elif mutation == 'missing': projection['panels'].pop()
    elif mutation == 'binding': payload['binding_state'] = 'admitted'
    elif mutation == 'claim_ref': projection['panels'][0]['headline']['refs'].append('fixture:unserved')
    else: projection['panels'][3]['accounting'][0]['outcome_refs'][0] = 'fixture:wrong_total'
    with pytest.raises(ClaimInputError, match='^INVALID_CLAIM_VIEW$'):
        cr.validate_view(payload)


def test_payload_byte_limit_counts_utf8_not_characters(monkeypatch):
    inputs = tuple(company(s) for s in ROSTER)
    encoded = cr.encode_communications_payload(inputs)
    assert len(encoded) > len(encoded.decode('utf-8'))
    monkeypatch.setattr(cr, 'MAX_VIEW_BYTES', len(encoded))
    assert cr.encode_communications_payload(inputs) == encoded
    monkeypatch.setattr(cr, 'MAX_VIEW_BYTES', len(encoded) - 1)
    with pytest.raises(ClaimInputError, match='^CLAIM_OUTPUT_LIMIT$'):
        cr.encode_communications_payload(inputs)


def test_payload_oversize_is_refused_before_schema_and_never_truncated():
    payload = payload_example()
    payload['oversize'] = '界' * 100000
    with pytest.raises(ClaimInputError, match='^CLAIM_OUTPUT_LIMIT$'):
        cr.validate_view(payload)


def test_payload_validation_does_not_mutate_the_candidate():
    payload = payload_example()
    before = deepcopy(payload)
    cr.validate_view(payload)
    assert payload == before
    assert payload['projection']['panels'][0]['limitation_zh']


def test_committed_domain_schema_closes_every_object_and_is_valid_draft_202012():
    from jsonschema import Draft202012Validator
    path = Path(__file__).resolve().parents[1] / 'contracts/market_ontology/communications_business_research.v1.schema.json'
    assert path.is_file(), 'The domain response needs its committed schema, not an unregistered Python-only shape.'
    schema = json.loads(path.read_text())
    Draft202012Validator.check_schema(schema)
    def walk(value):
        if isinstance(value, dict):
            if value.get('type') == 'object':
                assert value.get('additionalProperties') is False
            for child in value.values(): walk(child)
        elif isinstance(value, list):
            for child in value: walk(child)
    walk(schema)
    assert not list(Draft202012Validator(schema).iter_errors(payload_example()))


@pytest.mark.parametrize('mutation', ['metric', 'exact_support', 'guide_period', 'guide_currency'])
def test_payload_validator_refuses_misleading_embedded_measurement_metadata(mutation):
    payload = payload_example()
    panel = payload['projection']['panels'][0]
    current = panel['measures'][0]['current']
    if mutation == 'metric': current['metric'] = 'costs'
    elif mutation == 'exact_support':
        current['support_basis'] = 'exact'
        current['support'] = {'lower':'60000','upper':'62000','lower_inclusive':True,'upper_inclusive':True}
    elif mutation == 'guide_period': panel['original_guidance']['period'] = ['2026-07-01','2026-09-30']
    else: panel['original_guidance']['currency'] = 'EUR'
    with pytest.raises(ClaimInputError, match='^INVALID_CLAIM_VIEW$'):
        cr.validate_view(payload)


@pytest.mark.parametrize('bad', [None, 4, 'not a payload', [], {'schema':'other'}])
def test_payload_malformed_outer_shape_returns_fixed_refusal(bad):
    with pytest.raises(ClaimInputError, match='^INVALID_CLAIM_VIEW$'):
        cr.validate_view(bad)


def test_payload_invalid_unicode_is_sanitized_without_a_serializer_trace():
    payload = payload_example()
    payload['projection']['panels'][0]['limitation_en'] = '\ud800PRIVATE_CANARY'
    with pytest.raises(ClaimInputError) as error:
        cr.validate_view(payload)
    assert str(error.value) == 'INVALID_CLAIM_VIEW'


def test_payload_cycle_is_bounded_before_json_or_schema_traversal():
    payload = payload_example()
    payload['cycle'] = payload
    with pytest.raises(ClaimInputError, match='^CLAIM_OUTPUT_LIMIT$'):
        cr.validate_view(payload)


def test_payload_never_invokes_mapping_subclass_callbacks():
    class Hostile(dict):
        def items(self):
            raise AssertionError('An untrusted callback ran')
    with pytest.raises(ClaimInputError, match='^INVALID_CLAIM_VIEW$'):
        cr.validate_view(Hostile(payload_example()))


@pytest.mark.parametrize('value', [D('123456789012345678901234567890123456789012345678E+32'), D('1E-32'), D('100.0000')])
def test_payload_roundtrip_accepts_full_bounded_source_decimal_range(value):
    item = replace_record(company(), 0, value=value)
    with localcontext() as context:
        context.prec = 2
        context.clear_flags()
        encoded = cr.encode_communications_payload((item,))
        payload = json.loads(encoded)
        assert payload['projection']['panels'][0]['measures'][0]['current']['value'] == format(value, 'f')
        assert context.prec == 2 and not any(context.flags.values())


def test_payload_schema_never_requests_remote_reference_resolution():
    path = Path(__file__).resolve().parents[1] / 'contracts/market_ontology/communications_business_research.v1.schema.json'
    schema = json.loads(path.read_text())
    def walk(value):
        if type(value) is dict:
            if '$ref' in value: assert value['$ref'].startswith('#/$defs/')
            for child in value.values(): walk(child)
        elif type(value) is list:
            for child in value: walk(child)
    walk(schema)
