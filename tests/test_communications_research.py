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
