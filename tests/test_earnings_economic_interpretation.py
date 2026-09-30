from decimal import Context, Decimal, ROUND_CEILING, ROUND_DOWN, localcontext
from fractions import Fraction
import ast
import copy
from datetime import date, datetime
import hashlib
import json
import math
import random

import pytest

from engine.earnings_narrative import economic_interpretation
from engine.earnings_narrative.economic_interpretation import (
    AUTHORITY_KEYS,
    CODE_REVISION,
    FINDING_ORDER,
    FINDING_TEXT,
    SEMANTIC_REVISION,
    TOP_LEVEL_KEYS,
    EconomicInterpretationError,
    UnsupportedInterpretationVersion,
    build_economic_interpretation,
    compare_eps,
    family_lookup,
    format_value_and_unit,
    owner_lookup,
    validate_economic_interpretation,
)
from tests.earnings_economic_fixtures import FISCAL_SCOPE
from tests.earnings_economic_interpretation_fixtures import _case, build_case_interpretation
from engine.company_intelligence import economic_observations
from engine.company_intelligence.economic_observations import validate_selected_facts
from engine.company_intelligence.pg_profile import PG_DEFINITIONS


CAUSED_OUTCOMES = {
    'headline_positive_organic_flat': ('finding', 'reported_vs_organic_difference'),
    'reported_core_opposite_direction': ('finding', 'reported_vs_core_earnings_disagreement'),
    'negative_prior_eps': ('declined_comparison', 'nonpositive_prior'),
    'zero_prior_eps': ('declined_comparison', 'nonpositive_prior'),
    'reported_negative_organic_positive': ('finding', 'reported_vs_organic_difference'),
    'eps_flat_core_rises': ('finding', 'reported_vs_core_earnings_disagreement'),
    'missing_demand_context': ('typed_absent', 'pg_price_contribution_pp', 'no_span_addressable_evidence'),
    'unlocated_outcome': ('typed_absent', 'pg_mix_contribution_pp', 'no_span_addressable_evidence'),
    'segment_and_reconciliation_absent': ('typed_absent', 'pg_core_reconciliation_context', 'no_span_addressable_evidence'),
    'conflict_outcome': ('typed_absent', 'pg_total_volume_growth_pct', 'cross_check_conflict'),
    'refused_document_outcome': ('declined_comparison', 'no_span_addressable_evidence'),
    'combined_volume_mix': ('typed_absent', 'pg_total_volume_growth_pct', 'no_span_addressable_evidence'),
}


def _has_caused_outcome(payload, outcome):
    kind, expected = outcome[0], outcome[1]
    if kind == 'finding':
        return expected in {item['rule_id'] for item in payload['findings']}
    if kind == 'declined_comparison':
        return any(
            item['state'] in {'declined', 'not_comparable'}
            and item['result']['reason'] == expected
            for item in payload['comparisons']
        )
    return any(
        item['metric'] == expected and item.get('typed_absence', {}).get('reason') == outcome[2]
        for item in payload['observations']
    )


@pytest.mark.parametrize('case', sorted(CAUSED_OUTCOMES))
def test_fixture_edit_causes_its_declared_outcome(case):
    base = build_case_interpretation('identical_inputs')
    edited = build_case_interpretation(case)
    outcome = CAUSED_OUTCOMES[case]
    assert _has_caused_outcome(edited, outcome)
    assert not _has_caused_outcome(base, outcome)


def test_positive_headline_does_not_become_positive_organic_demand():
    result = build_case_interpretation('headline_positive_organic_flat')
    codes = {item['rule_id'] for item in result['findings']}
    assert 'reported_vs_organic_difference' in codes
    assert 'consumer_demand_unchanged' not in codes
    assert all(value is False for value in result['authority'].values())
    assert 'consensus' in {item['subject'] for item in result['missing_context']}


def test_zero_prior_has_no_invented_growth_rate():
    result = compare_eps(Decimal('1.20'), Decimal('0'), precision=None)
    assert result['state'] == 'not_comparable'
    assert result['value'] is None
    assert result['reason'] == 'nonpositive_prior'


def test_closed_shape_and_authority_are_exact():
    result = build_case_interpretation('identical_inputs')
    assert tuple(result) == TOP_LEVEL_KEYS
    assert len(TOP_LEVEL_KEYS) == 14
    assert tuple(result['authority']) == AUTHORITY_KEYS
    assert result['authority'] == {key: False for key in AUTHORITY_KEYS}


def test_combined_volume_mix_never_becomes_pure_volume():
    result = build_case_interpretation('combined_volume_mix')
    assert 'positive_organic_nonpositive_pure_volume' not in {x['rule_id'] for x in result['findings']}
    metric = 'pg_total_volume_growth_pct'
    observation = next(x for x in result['observations'] if x['metric'] == metric)
    assert observation['typed_absence']['subject'] == metric + ' combined volume/mix'


def test_reported_and_core_opposite_directions_disagree():
    result = build_case_interpretation('reported_core_opposite_direction')
    assert 'reported_vs_core_earnings_disagreement' in {x['rule_id'] for x in result['findings']}


@pytest.mark.parametrize('case', ['negative_prior_eps', 'zero_prior_eps'])
def test_nonpositive_prior_is_not_comparable(case):
    result = build_case_interpretation(case)
    comparison = result['comparisons'][0]
    assert comparison['state'] == 'not_comparable'
    assert comparison['result']['value'] is None
    assert comparison['result']['reason'] == 'nonpositive_prior'


def test_uncertainty_interval_touching_zero_refuses_rate():
    result = compare_eps(Decimal('1.00'), Decimal('0.02'), precision=2, uncertainty=Decimal('0.03'))
    assert result == {
        'state': 'not_comparable', 'value': None,
        'reason': 'uncertainty_interval_touches_zero',
        'formula': '(current / prior - 1) * 100',
    }


def test_optional_absence_leaves_supported_explanation():
    result = build_case_interpretation('segment_and_reconciliation_absent')
    assert result['quality']['supported'] is True
    assert {'pg_core_reconciliation_context', 'pg_beauty_organic_sales_growth_pct'} <= {
        x['subject'] for x in result['missing_context']
    }
    assert 'incomplete_margin_to_cash_bridge' in {x['rule_id'] for x in result['findings']}


def test_twenty_five_comparison_rows_are_refused():
    with pytest.raises(EconomicInterpretationError, match='comparisons exceed 24'):
        build_case_interpretation('twenty_five_comparisons')


def test_fake_fact_selector_is_refused():
    with pytest.raises(EconomicInterpretationError, match='selected fact handle is absent'):
        build_case_interpretation('fake_fact_selector')


def test_changed_code_version_preserves_native_clocks():
    baseline = build_case_interpretation('changed_code_version')
    monkeypatch_code = 'e' * 64
    economic_interpretation.CODE_REVISION = monkeypatch_code
    try:
        changed = build_case_interpretation('changed_code_version', code_revision=monkeypatch_code)
    finally:
        economic_interpretation.CODE_REVISION = CODE_REVISION
    assert changed['interpretation_id'] != baseline['interpretation_id']
    for field in ('source_revision', 'source_available_at', 'first_observed_at'):
        assert changed['clocks'][field] == baseline['clocks'][field]


def test_identical_inputs_are_deterministic(monkeypatch):
    clock = {'now': 1.0}
    monkeypatch.setattr(
        economic_interpretation, 'time',
        type('Clock', (), {'time': staticmethod(lambda: clock['now'])}),
        raising=False,
    )
    left = build_case_interpretation('identical_inputs')
    clock['now'] = 2.0
    right = build_case_interpretation('identical_inputs')
    assert left['interpretation_id'] == right['interpretation_id']


def test_comparison_input_swapped_to_another_period_fails():
    payload = build_case_interpretation('identical_inputs')
    inputs = payload['comparisons'][0]['inputs']
    inputs[0]['period'], inputs[1]['period'] = inputs[1]['period'], inputs[0]['period']
    workspace, texts = _case('identical_inputs')
    with pytest.raises(EconomicInterpretationError, match='stored interpretation does not replay'):
        validate_economic_interpretation(payload, workspaces=workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE)


def test_tampered_stored_result_fails_trusted_validation():
    payload = build_case_interpretation('identical_inputs')
    payload['comparisons'][0]['result']['value'] = '99.99'
    workspace, texts = _case('identical_inputs')
    with pytest.raises(EconomicInterpretationError, match='stored interpretation does not replay'):
        validate_economic_interpretation(payload, workspaces=workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE)


def test_source_correction_invalidates_dependent_handles():
    payload = build_case_interpretation('identical_inputs')
    original_workspace, original_texts = _case('identical_inputs')
    original_body = next(iter(original_texts.values()))
    corrected_body = original_body.replace('$3.07', '$3.08')
    corrected_workspace, corrected_texts = _case('identical_inputs', body=corrected_body)
    assert corrected_workspace['_source_sha256'] != original_workspace['_source_sha256']
    with pytest.raises(EconomicInterpretationError, match='stored interpretation identity does not replay'):
        validate_economic_interpretation(
            payload, workspaces=corrected_workspace,
            source_texts=corrected_texts, fiscal_scope=FISCAL_SCOPE,
        )


def test_fiscal_period_text_fields_do_not_change_pairing():
    workspace, texts = _case('identical_inputs')
    workspace = dict(workspace)
    workspace['fiscal_period'] = dict(workspace['fiscal_period'], year='3026', quarter='14')
    with pytest.raises(EconomicInterpretationError, match='native observations are refused'):
        build_economic_interpretation(
            workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE,
            selection={'facts': None, 'currentness': None},
            semantic_revision=SEMANTIC_REVISION, code_revision=CODE_REVISION,
        )


def test_unsupported_historical_version_is_typed_unavailable():
    result = build_case_interpretation(
        'identical_inputs', code_revision='0' * 63,
    )
    assert result['quality'] == {
        'supported': False, 'state': 'unavailable',
        'reason': 'unsupported interpretation version',
    }
    assert result['authority'] == {key: False for key in AUTHORITY_KEYS}


def test_unlocated_outcome_is_never_zero():
    result = build_case_interpretation('unlocated_outcome')
    missing = {x['subject']: x['reason'] for x in result['missing_context']}
    assert missing['pg_mix_contribution_pp'] == 'no_span_addressable_evidence'


def test_conflict_outcome_carries_envelope_reason():
    result = build_case_interpretation('conflict_outcome')
    missing = {x['subject']: x['reason'] for x in result['missing_context']}
    assert missing['pg_total_volume_growth_pct'] == 'cross_check_conflict'


def test_refused_document_outcome_declines_comparison():
    result = build_case_interpretation('refused_document_outcome')
    comparison = result['comparisons'][0]
    assert comparison['state'] == 'declined'
    assert comparison['result']['reason'] == 'no_span_addressable_evidence'


def test_r3_paths_are_present_for_both_fixture_cases():
    for case in ('identical_inputs', 'segment_and_reconciliation_absent'):
        result = build_case_interpretation(case)
        assert result['authority'] == {key: False for key in AUTHORITY_KEYS}
        for observation in result['observations']:
            for key in ('fact_id', 'family', 'group', 'label', 'period', 'basis', 'value_and_unit'):
                assert key in observation
            assert set(observation['label']) == {'en', 'zh'}
            if observation['value_and_unit'] is not None:
                assert observation['value_and_unit']['en']
                assert observation['value_and_unit']['zh']
            else:
                assert 'typed_absence' in observation or 'source_text' in observation
        for key in ('fiscal_period', 'source_accepted', 'source_currentness'):
            assert key in result['clocks']


SPEC_LABEL_TABLE = {
    'pg_reported_sales_growth_pct': ('reported_sales_growth', 'demand', 'reported', 'current', 'Reported sales growth', '报告销售额增长'),
    'pg_organic_sales_growth_pct': ('organic_sales_growth', 'demand', 'organic', 'current', 'Organic sales growth', '有机销售额增长'),
    'pg_total_volume_growth_pct': ('total_volume_growth', 'demand', 'reported', 'current', 'Total volume growth', '总销量增长'),
    'pg_organic_volume_growth_pct': ('organic_volume_growth', 'demand', 'organic', 'current', 'Organic volume growth', '有机销量增长'),
    'pg_price_contribution_pp': ('price_contribution', 'demand', 'reported', 'current', 'Price contribution', '价格贡献'),
    'pg_mix_contribution_pp': ('mix_contribution', 'demand', 'reported', 'current', 'Mix contribution', '结构贡献'),
    'pg_fx_contribution_pp': ('fx_contribution', 'demand', 'reported', 'current', 'FX contribution', '汇率贡献'),
    'pg_other_contribution_pp': ('other_contribution', 'demand', 'reported', 'current', 'Other contribution', '其他贡献'),
    'pg_diluted_eps': ('reported_diluted_eps', 'earnings', 'reported', 'current', 'Reported diluted EPS', '报告稀释每股收益'),
    'pg_prior_diluted_eps': ('prior_reported_diluted_eps', 'earnings', 'reported', 'prior', 'Prior reported diluted EPS', '上期报告稀释每股收益'),
    'pg_reported_eps_growth_pct': ('reported_eps_growth', 'earnings', 'reported', 'current', 'Reported EPS growth', '报告每股收益增长'),
    'pg_core_eps': ('core_eps', 'earnings', 'core', 'current', 'Core EPS', '核心每股收益'),
    'pg_prior_core_eps': ('prior_core_eps', 'earnings', 'core', 'prior', 'Prior core EPS', '上期核心每股收益'),
    'pg_core_eps_growth_pct': ('core_eps_growth', 'earnings', 'core', 'current', 'Core EPS growth', '核心每股收益增长'),
    'pg_core_reconciliation_context': ('core_reconciliation_context', 'earnings', 'core', 'current', 'Core EPS reconciliation', '核心每股收益调节说明'),
}


SPEC_SEGMENT_LABELS = {
    'pg_beauty_organic_sales_growth_pct': 'Beauty',
    'pg_grooming_organic_sales_growth_pct': 'Grooming',
    'pg_health_care_organic_sales_growth_pct': 'Health Care',
    'pg_fabric_home_organic_sales_growth_pct': 'Fabric and Home Care',
    'pg_baby_feminine_family_organic_sales_growth_pct': 'Baby, Feminine and Family Care',
}


def test_spec_strings_are_exact():
    result = build_case_interpretation('identical_inputs')
    labels = {item['metric']: item['label'] for item in result['observations']}
    for metric, expected in SPEC_LABEL_TABLE.items():
        assert family_lookup(metric) == expected
        assert labels[metric] == {'en': expected[4], 'zh': expected[5]}
    owner_scopes = {
        definition.metric: definition.segment_scope
        for definition in PG_DEFINITIONS if definition.segment_scope is not None
    }
    assert owner_scopes == SPEC_SEGMENT_LABELS
    for metric, scope in SPEC_SEGMENT_LABELS.items():
        assert family_lookup(metric)[4:] == (scope, scope)
        assert labels[metric] == {'en': scope, 'zh': scope}
    groups = {item['metric']: item['group'] for item in result['observations']}
    assert {metric for metric, group in groups.items() if group == 'segment'} == set(SPEC_SEGMENT_LABELS)
    assert set(labels) == set(SPEC_LABEL_TABLE) | set(SPEC_SEGMENT_LABELS)
    assert set(economic_interpretation._DISPLAY) == set(SPEC_LABEL_TABLE) | set(SPEC_SEGMENT_LABELS)
    values = {item['metric']: item['value_and_unit'] for item in result['observations']}
    assert values['pg_reported_sales_growth_pct'] == {'en': '3.0%', 'zh': '3.0%'}
    assert values['pg_fx_contribution_pp'] == {'en': '-1.0 pp', 'zh': '-1.0个百分点'}
    assert values['pg_diluted_eps'] == {'en': '$3.07', 'zh': '3.07美元'}
    assert result['clocks']['fiscal_period'] == {
        'en': 'Quarter ended June 30, 2026', 'zh': '截至2026年6月30日的季度'
    }
    assert result['clocks']['source_accepted'] == {
        'en': 'Jul 29, 2026, 17:00 UTC', 'zh': '2026年7月29日 17:00 UTC'
    }

def test_currentness_contract_and_identity():
    clock = '2026-07-29T17:01:00Z'
    states = (
        ('up_to_date', clock), ('newer_source_pending', clock),
        ('currentness_unverified', None),
    )
    baseline = None
    for state, source_clock in states:
        result = build_case_interpretation(
            'identical_inputs', selection={'facts': None, 'currentness': {'state': state, 'source_clock': source_clock}}
        )
        assert result['selection']['currentness'] == state
        assert result['selection']['currentness_observed_at'] == source_clock
        assert result['clocks']['source_currentness'] == (
            {'en': 'Jul 29, 2026, 17:01 UTC', 'zh': '2026年7月29日 17:01 UTC'}
            if source_clock is not None else None
        )
        if baseline is not None:
            assert result['interpretation_id'] != baseline['interpretation_id']
            assert result['clocks']['source_revision'] == baseline['clocks']['source_revision']
            assert result['clocks']['correction'] == baseline['clocks']['correction']
        baseline = result
    default = build_case_interpretation('identical_inputs')
    assert default['selection']['currentness'] == 'currentness_unverified'
    assert default['selection']['currentness_observed_at'] is None
    assert default['clocks']['source_currentness'] is None
    invalid = (
        {'facts': None, 'currentness': {'state': 'up_to_date', 'source_clock': None}},
        {'facts': None, 'currentness': {'state': 'currentness_unverified', 'source_clock': clock}},
        {'facts': None, 'currentness': {'state': 'unknown', 'source_clock': clock}},
        {'facts': None, 'currentness': {'state': 'up_to_date'}, 'extra': 1},
        [],
    )
    for selection in invalid:
        with pytest.raises(EconomicInterpretationError):
            build_case_interpretation('identical_inputs', selection=selection)


def test_display_and_owner_lookups_are_closed():
    with pytest.raises(EconomicInterpretationError):
        family_lookup('unknown_metric')
    with pytest.raises(EconomicInterpretationError):
        format_value_and_unit(Decimal('1'), 'unknown_unit')
    with pytest.raises(EconomicInterpretationError):
        owner_lookup('unknown_group')


@pytest.mark.parametrize('lookup,admitted', [
    (family_lookup, 'pg_core_eps'),
    (lambda unit: format_value_and_unit(Decimal('1'), unit), 'percent'),
    (owner_lookup, 'demand'),
], ids=['family_lookup', 'format_value_and_unit', 'owner_lookup'])
@pytest.mark.parametrize('kind', ['list', 'raiser', 'liar', 'str_subclass'])
def test_each_lookup_tests_the_type_before_it_reads_the_value(lookup, admitted, kind):
    assert lookup(admitted) is not None
    value = {
        'list': [admitted], 'raiser': _Raiser(), 'liar': _Liar('not_in_any_table'), 'str_subclass': _Str(admitted),
    }[kind]
    with pytest.raises(EconomicInterpretationError, match='is absent from the closed'):
        lookup(value)


@pytest.mark.parametrize('kind', ['list', 'raiser', 'liar', 'str_subclass'])
def test_owner_lookup_tests_the_metric_type_before_it_reads_the_value(kind):
    metric = {
        'list': ['pg_core_reconciliation_context'], 'raiser': _Raiser(),
        'liar': _Liar('pg_core_reconciliation_context'),
        'str_subclass': _Str('pg_core_reconciliation_context'),
    }[kind]
    assert owner_lookup('demand', metric) == owner_lookup('demand')
    assert owner_lookup('demand', metric) != 'reconciliation'
    assert owner_lookup('demand', 'pg_core_reconciliation_context') == 'reconciliation'


@pytest.mark.parametrize('kind', ['list', 'raiser', 'liar', 'str_subclass'])
def test_format_value_and_unit_tests_the_value_type_before_it_reads_the_value(kind):
    value = {
        'list': [Decimal('1')], 'raiser': _Raiser(), 'liar': _Liar('1'),
        'str_subclass': _Str('1'),
    }[kind]
    with pytest.raises(EconomicInterpretationError, match='numeric input is not a decimal-compatible value'):
        format_value_and_unit(value, 'percent')
    assert format_value_and_unit(Decimal('1'), 'percent') is not None


def test_compare_eps_uncertainty_is_provided():
    assert compare_eps(Decimal('1.64'), Decimal('1.50'), precision=2)['value'] == '9.33'
    assert compare_eps(Decimal('0.03'), Decimal('0.01'), precision=2)['value'] == '200.00'
    for uncertainty in (Decimal('0.03'), Decimal('0.02')):
        result = compare_eps(Decimal('1.00'), Decimal('0.02'), precision=2, uncertainty=uncertainty)
        assert result['reason'] == 'uncertainty_interval_touches_zero'
        assert result['value'] is None
    assert compare_eps(Decimal('1.00'), Decimal('0.01'), precision=2, uncertainty=Decimal('0.005'))['state'] == 'comparable'
    for uncertainty in (Decimal('-0.01'), Decimal('NaN'), True):
        with pytest.raises(EconomicInterpretationError):
            compare_eps(Decimal('1'), Decimal('.01'), precision=None, uncertainty=uncertainty)


@pytest.mark.parametrize('prior', ['0', '-1'])
@pytest.mark.parametrize('bad_uncertainty', [True, 'x', '-1', [1]])
def test_compare_eps_parses_uncertainty_before_outcomes(bad_uncertainty, prior):
    with pytest.raises(EconomicInterpretationError):
        compare_eps('1.64', prior, precision=2, uncertainty=bad_uncertainty)


@pytest.mark.parametrize('prior', ['0', '-1'])
@pytest.mark.parametrize('bad_precision', [-1, True, 2.0, '2'])
def test_compare_eps_parses_precision_before_outcomes(bad_precision, prior):
    with pytest.raises(EconomicInterpretationError):
        compare_eps('1.64', prior, precision=bad_precision)


@pytest.mark.parametrize('prior', ['0', '-1'])
@pytest.mark.parametrize('bad_current', [True, None, float('nan')])
def test_compare_eps_parses_current_before_outcomes(bad_current, prior):
    with pytest.raises(EconomicInterpretationError):
        compare_eps(bad_current, prior, precision=2)


@pytest.mark.parametrize('current,prior', [('1.64', '1.52'), ('1e400', '1')])
def test_compare_eps_arithmetic_stays_guarded(current, prior):
    with pytest.raises(EconomicInterpretationError, match='EPS growth arithmetic is not defined'):
        compare_eps(current, prior, precision=40 if current == '1.64' else 2)


HUGE = '9.' + '9' * 40 + 'e999999'


def test_compare_eps_decides_the_interval_without_arithmetic_that_can_overflow():
    touching = compare_eps('1.64', '1', precision=2, uncertainty=HUGE)
    assert touching == {
        'state': 'not_comparable', 'value': None,
        'reason': 'uncertainty_interval_touches_zero', 'formula': '(current / prior - 1) * 100',
    }
    clear = compare_eps('1.64', HUGE, precision=2, uncertainty='1')
    assert (clear['state'], clear['value'], clear['reason']) == ('comparable', '-100.00', None)
    with pytest.raises(EconomicInterpretationError, match='EPS growth arithmetic is not defined'):
        compare_eps(HUGE, '1e-999999', precision=2)


def _all_handles(case):
    workspace, texts = _case(case)
    rows = validate_selected_facts(workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE)
    return [
        {
            'workspace_generation_id': workspace['generation_id'],
            'event_id': row['event_id'],
            'fact_id': row['fact_id'],
        }
        for row in rows
    ]


@pytest.mark.parametrize('case', ['identical_inputs', 'segment_and_reconciliation_absent'])
def test_selection_order_cannot_change_payload_or_identity(case):
    handles = _all_handles(case)
    shuffled = list(handles)
    random.Random(8232).shuffle(shuffled)
    five = shuffled[:5]
    facts_orders = [None, list(handles), list(reversed(handles)), shuffled, five, list(reversed(five))]
    payloads = []
    for facts in facts_orders:
        payloads.append(build_case_interpretation(case, selection={
            'facts': facts, 'currentness': None,
        }))
    assert len({json.dumps(payload, sort_keys=True) for payload in payloads}) == 2
    workspace, texts = _case(case)
    expected_ids = [row['fact_id'] for row in validate_selected_facts(
        workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE
    )]
    selected_ids = {item['fact_id'] for item in payloads[3]['observations']}
    assert [item['fact_id'] for item in payloads[3]['observations']] == [
        fact_id for fact_id in expected_ids if fact_id in selected_ids
    ]
    for payload, facts in zip(payloads[4:], (five, list(reversed(five)))):
        assert [item['fact_id'] for item in payload['observations']] == [
            fact_id for fact_id in expected_ids if fact_id in {item['fact_id'] for item in facts}
        ]


@pytest.mark.parametrize('case', ['identical_inputs', 'segment_and_reconciliation_absent'])
def test_duplicate_selection_is_refused(case):
    duplicate = _all_handles(case)[0]
    with pytest.raises(EconomicInterpretationError):
        build_case_interpretation(case, selection={
            'facts': [duplicate, dict(duplicate)], 'currentness': None,
        })


@pytest.mark.parametrize('case', [
    'identical_inputs', 'headline_positive_organic_flat',
    'reported_core_opposite_direction', 'negative_prior_eps', 'zero_prior_eps',
    'reported_negative_organic_positive', 'eps_flat_core_rises',
    'missing_demand_context', 'unlocated_outcome',
    'segment_and_reconciliation_absent', 'conflict_outcome',
    'refused_document_outcome', 'combined_volume_mix',
])
def test_finding_handles_are_selected_observations(case):
    payload = build_case_interpretation(case)
    observation_handles = [item['handle'] for item in payload['observations']]
    for finding in payload['findings']:
        if finding['rule_id'] in {'incomplete_margin_to_cash_bridge', 'missing_consensus'}:
            assert finding['input_handles'] == []
            continue
        assert finding['input_handles']
        for handle in finding['input_handles']:
            assert set(handle) == {'workspace_generation_id', 'event_id', 'fact_id'}
            assert handle in observation_handles
            assert handle is not None


def _selection_with_metrics(*metrics, case='identical_inputs'):
    workspace, texts = _case(case)
    rows = validate_selected_facts(workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE)
    handles = [
        {
            'workspace_generation_id': workspace['generation_id'],
            'event_id': row['event_id'],
            'fact_id': row['fact_id'],
        }
        for row in rows if row['metric'] in metrics
    ]
    return {'facts': handles, 'currentness': None}



def test_unselected_comparison_never_invents_an_absence_reason():
    selection = _selection_with_metrics('pg_reported_sales_growth_pct')
    payload = build_case_interpretation('identical_inputs', selection=selection)
    declined = [
        item for item in payload['comparisons']
        if all(input_['handle']['fact_id'] is None for input_ in item['inputs'])
    ]
    assert len(declined) == 2
    assert all(
        item['result']['reason'] == 'not_selected' and item['result']['detail'] is None
        for item in declined
    )


def test_selected_typed_absent_comparison_uses_task_one_reason():
    payload = build_case_interpretation('refused_document_outcome')
    comparison = payload['comparisons'][0]
    assert comparison['result']['reason'] == 'no_span_addressable_evidence'
    assert comparison['result']['detail'] == 'envelope_refused:not_ex_99_1'


TASK_ONE_ABSENCE = {
    'state': 'not_comparable', 'value': None,
    'reason': 'no_span_addressable_evidence', 'detail': 'envelope_refused:not_ex_99_1',
}
NOT_SELECTED = {'state': 'not_comparable', 'value': None, 'reason': 'not_selected', 'detail': None}


@pytest.mark.parametrize('metric', ['pg_diluted_eps', 'pg_prior_diluted_eps'])
def test_one_selected_typed_absent_side_gives_task_one_reason(metric):
    selection = _selection_with_metrics(metric, case='refused_document_outcome')
    assert len(selection['facts']) == 1
    payload = build_case_interpretation('refused_document_outcome', selection=selection)
    assert [item['result'] for item in payload['comparisons']] == [TASK_ONE_ABSENCE, NOT_SELECTED]


@pytest.mark.parametrize('metric', ['pg_diluted_eps', 'pg_prior_diluted_eps'])
def test_one_selected_side_with_a_value_is_not_selected(metric):
    selection = _selection_with_metrics(metric)
    assert len(selection['facts']) == 1
    payload = build_case_interpretation('identical_inputs', selection=selection)
    assert [item['result'] for item in payload['comparisons']] == [NOT_SELECTED, NOT_SELECTED]


def _comparison_side(role, kind):
    metric = {'current': 'pg_diluted_eps', 'prior': 'pg_prior_diluted_eps'}[role]
    if kind == 'unselected':
        return {}
    side = {'metric': metric, 'event_id': 'evt', 'fact_id': f'fact_{role}'}
    if kind == 'present':
        side['value'] = 3.07
    else:
        side['typed_absence'] = {'reason': f'{role}_reason', 'detail': f'{role}_detail'}
    return side


@pytest.mark.parametrize('current,prior,reason,detail', [
    ('absent', 'absent', 'current_reason', 'current_detail'),
    ('absent', 'present', 'current_reason', 'current_detail'),
    ('absent', 'unselected', 'current_reason', 'current_detail'),
    ('present', 'absent', 'prior_reason', 'prior_detail'),
    ('unselected', 'absent', 'prior_reason', 'prior_detail'),
    ('present', 'unselected', 'not_selected', None),
    ('unselected', 'present', 'not_selected', None),
    ('unselected', 'unselected', 'not_selected', None),
])
def test_declined_comparison_reports_the_selected_typed_absence_current_side_first(
    current, prior, reason, detail
):
    comparison = economic_interpretation._comparison(
        {'generation_id': ''}, _comparison_side('current', current), _comparison_side('prior', prior),
        FISCAL_SCOPE, None,
    )
    assert comparison['state'] == 'declined'
    assert comparison['result'] == {
        'state': 'not_comparable', 'value': None, 'reason': reason, 'detail': detail,
    }


def test_unavailable_payload_has_no_missing_context_items():
    payload = build_case_interpretation('identical_inputs', code_revision='0' * 63)
    assert payload['missing_context'] == []
    assert payload['quality']['reason'] == 'unsupported interpretation version'
    assert payload['build']['code_revision'] == '0' * 63


@pytest.mark.parametrize('case', [
    'identical_inputs', 'headline_positive_organic_flat',
    'reported_core_opposite_direction', 'negative_prior_eps', 'zero_prior_eps',
    'reported_negative_organic_positive', 'eps_flat_core_rises',
    'missing_demand_context', 'unlocated_outcome',
    'segment_and_reconciliation_absent', 'conflict_outcome',
    'refused_document_outcome', 'combined_volume_mix',
])
def test_every_missing_context_item_has_an_owner(case):
    payload = build_case_interpretation(case)
    assert {item['owner'] for item in payload['missing_context']} <= {
        'demand', 'segments', 'earnings', 'reconciliation', 'margin_to_cash', 'consensus',
    }
    assert all(item['owner'] for item in payload['missing_context'])


def test_trusted_boundary_rejects_display_and_currentness_edits():
    payload = build_case_interpretation(
        'identical_inputs',
        selection={'facts': None, 'currentness': {'state': 'up_to_date', 'source_clock': '2026-07-29T17:01:00Z'}},
    )
    workspace, texts = _case('identical_inputs')
    edits = (
        lambda value: value['selection'].__setitem__('currentness', 'newer_source_pending'),
        lambda value: value['observations'][0]['label'].__setitem__('zh', '错误'),
        lambda value: value['observations'][0]['value_and_unit'].__setitem__('en', '99.9%'),
        lambda value: value.__setitem__('issuer', {'ticker': 'WRONG'}),
        lambda value: value.__setitem__('event_id', 'wrong'),
        lambda value: value['build'].__setitem__('deterministic', False),
        lambda value: value.__setitem__('quality', {'supported': True, 'state': 'wrong'}),
        lambda value: value.__setitem__('next_evidence', []),
    )
    for edit in edits:
        stored = copy.deepcopy(payload)
        edit(stored)
        with pytest.raises(EconomicInterpretationError):
            validate_economic_interpretation(
                stored, workspaces=workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE
            )


def test_trusted_boundary_rejects_every_wrong_typed_top_level_value():
    workspace, texts, payload = _baseline(ABSENT)
    validate_economic_interpretation(payload, workspaces=workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE)
    for key in TOP_LEVEL_KEYS:
        for value in (5, 'x', [1], {'k': 1}, None, True):
            if value == payload[key]:
                continue
            stored = copy.deepcopy(payload)
            stored[key] = value
            with pytest.raises(EconomicInterpretationError):
                validate_economic_interpretation(
                    stored, workspaces=workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE
                )
    for observations in ([1], [{'handle': 5}]):
        stored = copy.deepcopy(payload)
        stored['observations'] = observations
        with pytest.raises(EconomicInterpretationError):
            validate_economic_interpretation(
                stored, workspaces=workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE
            )


def test_owner_and_general_missing_context_rule():
    absent = build_case_interpretation('segment_and_reconciliation_absent')['missing_context']
    expected_prefix = [
        'pg_core_reconciliation_context', 'pg_beauty_organic_sales_growth_pct',
        'pg_grooming_organic_sales_growth_pct', 'pg_health_care_organic_sales_growth_pct',
        'pg_fabric_home_organic_sales_growth_pct', 'pg_baby_feminine_family_organic_sales_growth_pct',
        'margin_to_cash', 'consensus',
    ]
    assert [item['subject'] for item in absent][-len(expected_prefix):] == expected_prefix
    demand = build_case_interpretation('missing_demand_context')['missing_context']
    item = next(value for value in demand if value['subject'] == 'pg_price_contribution_pp')
    assert item['owner'] == 'demand'
    assert item['detail'] == 'No unique heading, row label, and column header identifies this observation.'
    demand_case = build_case_interpretation('unlocated_outcome')['missing_context']
    assert any(
        value['subject'] == 'pg_mix_contribution_pp' and value['owner'] == 'demand'
        for value in demand_case
    )


def test_unforged_outcome_and_demand_absence_come_from_task_one():
    unlocated = build_case_interpretation('unlocated_outcome')
    row = next(item for item in unlocated['observations'] if item['metric'] == 'pg_mix_contribution_pp')
    assert row['typed_absence']['reason'] == 'no_span_addressable_evidence'
    assert row['typed_absence']['detail'] == 'No unique heading, row label, and column header identifies this observation.'
    demand = build_case_interpretation('missing_demand_context')
    assert [item['subject'] for item in demand['missing_context']].count('pg_price_contribution_pp') == 1


def test_revision_contract_is_closed_and_identity_follows_code():
    for revision in ('f' * 64, 'synthetic-code-revision-v1'):
        result = build_case_interpretation('identical_inputs', code_revision=revision)
        assert result['quality']['state'] == 'unavailable'
    baseline = build_case_interpretation('identical_inputs')
    stored = copy.deepcopy(baseline)
    stored['build']['code_revision'] = 'f' * 64
    workspace, texts = _case('identical_inputs')
    with pytest.raises(UnsupportedInterpretationVersion):
        validate_economic_interpretation(
            stored, workspaces=workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE
        )
    economic_interpretation.CODE_REVISION = 'e' * 64
    try:
        changed = build_case_interpretation('identical_inputs', code_revision='e' * 64)
        with pytest.raises(UnsupportedInterpretationVersion):
            validate_economic_interpretation(
                baseline, workspaces=workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE
            )
    finally:
        economic_interpretation.CODE_REVISION = CODE_REVISION
    assert changed['interpretation_id'] != baseline['interpretation_id']
    for field in ('source_revision', 'source_available_at', 'first_observed_at'):
        assert changed['clocks'][field] == baseline['clocks'][field]


def test_source_identity_is_bound_to_release_text():
    baseline = build_case_interpretation('identical_inputs')
    workspace, texts = _case('identical_inputs')
    for source in workspace['sources']:
        if source.get('kind') == 'issuer_release':
            source['source_sha256'] = '0' * 64
    changed = build_economic_interpretation(
        workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE,
        selection={'facts': None, 'currentness': None},
        semantic_revision=SEMANTIC_REVISION, code_revision=CODE_REVISION,
    )
    source_text = next(iter(texts.values()))
    assert changed['clocks']['source_revision'] != '0' * 64
    assert changed['interpretation_id'] == baseline['interpretation_id']
    assert changed['clocks']['source_revision'] == baseline['clocks']['source_revision']
    assert changed['clocks']['source_revision'] == hashlib.sha256(source_text.encode('utf-8')).hexdigest()


def test_pair_period_contract_is_probed_directly():
    workspace, texts = _case('identical_inputs')
    rows = validate_selected_facts(workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE)
    current = next(row for row in rows if row['metric'] == 'pg_diluted_eps')
    prior = next(row for row in rows if row['metric'] == 'pg_prior_diluted_eps')
    altered_prior = dict(prior, period='2025-05-31')
    with pytest.raises(EconomicInterpretationError, match='selected fiscal periods'):
        economic_interpretation._validate_pair(current, altered_prior, FISCAL_SCOPE)
    economic_interpretation._validate_pair(current, prior, FISCAL_SCOPE)


def test_rules_and_copy_follow_the_spec_tables():
    opposite = build_case_interpretation('reported_negative_organic_positive')
    assert 'reported_vs_organic_difference' in {item['rule_id'] for item in opposite['findings']}
    base = build_case_interpretation('identical_inputs')
    assert 'reported_vs_organic_difference' not in {item['rule_id'] for item in base['findings']}
    base_rule_ids = [item['rule_id'] for item in base['findings']]
    assert base_rule_ids.index('incomplete_margin_to_cash_bridge') < base_rule_ids.index('segment_scope_limitation')
    assert base_rule_ids[-1] == 'missing_consensus'
    absent = build_case_interpretation('segment_and_reconciliation_absent')
    assert 'segment_scope_limitation' not in {item['rule_id'] for item in absent['findings']}
    for result in (base, absent, build_case_interpretation('eps_flat_core_rises')):
        assert 'incomplete_margin_to_cash_bridge' in {item['rule_id'] for item in result['findings']}
        assert 'margin_to_cash' in {item['subject'] for item in result['missing_context']}
    assert 'reported_vs_core_earnings_disagreement' in {
        item['rule_id'] for item in build_case_interpretation('eps_flat_core_rises')['findings']
    }
    assert FINDING_ORDER == (
        'reported_vs_organic_difference', 'positive_organic_nonpositive_pure_volume',
        'reported_vs_core_earnings_disagreement', 'incomplete_margin_to_cash_bridge',
        'segment_scope_limitation', 'missing_consensus',
    )
    assert FINDING_TEXT == {
        'reported_vs_organic_difference': ('Reported and organic growth differ — check the source before acting.', '报告与有机增长不同——先核对来源再行动。'),
        'positive_organic_nonpositive_pure_volume': ('Organic rose but pure volume did not — watch — don\'t chase.', '有机增长而纯销量未增——先观察，不追入。'),
        'reported_vs_core_earnings_disagreement': ('Reported and core EPS differed — read the receipt first.', '报告与核心每股收益不同——先阅读凭证。'),
        'incomplete_margin_to_cash_bridge': ('Margin does not show profit or cash improvement — nothing to act on yet.', '利润率未显示利润或现金改善——暂无可执行事项。'),
        'segment_scope_limitation': ('Segments cover only those segments — check the source before acting.', '分部仅覆盖这些分部——先核对来源再行动。'),
        'missing_consensus': ('Consensus is unavailable — nothing to act on yet.', '缺少一致预期——暂无可执行事项。'),
    }


ABSENT = 'refused_document_outcome'
_BASELINES = {}


def _baseline(case='identical_inputs'):
    """A fixture case's workspace, source texts and built payload: built once, then copied for each caller.

    Every row of the `ABSENT` case is typed-absent.  Task 1 validates that in about a millisecond, and a release
    with values in about seventy, so tests of rules that read no row's content use `ABSENT`.
    """
    if case not in _BASELINES:
        workspace, texts = _case(case)
        _BASELINES[case] = (workspace, texts, build_economic_interpretation(
            workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE,
            selection={'facts': None, 'currentness': None},
            semantic_revision=SEMANTIC_REVISION, code_revision=CODE_REVISION,
        ))
    return copy.deepcopy(_BASELINES[case])


class _Str(str):
    pass


def _call_with_currentness(value):
    workspace, texts, _payload = _baseline(ABSENT)
    _build_with(
        workspace, texts, selection={'facts': None, 'currentness': {'state': 'up_to_date', 'source_clock': value}},
    )


def _validated_with_observed_at(value):
    workspace, texts, _payload = _baseline(ABSENT)
    payload = _build_with(workspace, texts, selection={'facts': None, 'currentness': CLOCKED})
    validate_economic_interpretation(payload, workspaces=workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE)
    payload['selection']['currentness_observed_at'] = value
    with pytest.raises(EconomicInterpretationError):
        validate_economic_interpretation(
            payload, workspaces=workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE
        )


def _built_with_lifecycle(field, value):
    workspace, texts, _payload = _baseline(ABSENT)
    workspace['lifecycle'][field] = value
    with pytest.raises(EconomicInterpretationError):
        build_economic_interpretation(
            workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE,
            selection={'facts': None, 'currentness': None},
            semantic_revision=SEMANTIC_REVISION, code_revision=CODE_REVISION,
        )


_INSTANT_VALUES = (
    '2026-13-01T00:00:00Z', '2026-00-10T00:00:00Z', '2026-02-31T00:00:00Z',
    '2026-01-01T00:00:60Z', '2026-01-01T00:00:99Z', '2026-07-29T24:00:00Z',
    '٢٠٢٦-٠٧-٢٩T17:00:00Z', '２０２６-07-29T17:00:00Z', '2026-7-29T17:00:00Z',
    '2026-07-29T17:00:00+00:00', _Str('2026-07-29T17:00:00Z'),
    b'2026-07-29T17:00:00Z', 0, True, ['2026-07-29T17:00:00Z'], {'at': 1},
)


@pytest.mark.parametrize('entry,value', [
    *[(f'currentness:{index}', value) for index, value in enumerate(_INSTANT_VALUES)],
    *[(f'validator:{index}', value) for index, value in enumerate(_INSTANT_VALUES)],
    *[(f'source_available_at:{index}', value) for index, value in enumerate(_INSTANT_VALUES)],
    *[(f'observed_at:{index}', value) for index, value in enumerate(_INSTANT_VALUES)],
])
def test_instants_are_parsed_once_at_every_boundary(entry, value):
    kind = entry.split(':', 1)[0]
    if kind == 'currentness':
        with pytest.raises(EconomicInterpretationError):
            _call_with_currentness(value)
    elif kind == 'validator':
        _validated_with_observed_at(value)
    else:
        _built_with_lifecycle('source_available_at' if kind == 'source_available_at' else 'observed_at', value)


_DATE_VALUES = (
    '2026-13-30', '2026-02-30', '2026-6-30', '٢٠٢٦-٠٦-٣٠',
    _Str('2026-06-30'), None, 20260630,
)


def _with_fiscal_scope(value):
    workspace, texts, _payload = _baseline(ABSENT)
    build_economic_interpretation(
        workspace, source_texts=texts, fiscal_scope=value,
        selection={'facts': None, 'currentness': None},
        semantic_revision=SEMANTIC_REVISION, code_revision=CODE_REVISION,
    )


@pytest.mark.parametrize('position,value', [
    (position, value) for position in range(4) for value in _DATE_VALUES
])
def test_dates_are_parsed_in_build_and_validate(position, value):
    scope = list(FISCAL_SCOPE)
    scope[position] = value
    with pytest.raises(EconomicInterpretationError, match='is not a canonical date'):
        _with_fiscal_scope(scope)
    workspace, texts, payload = _baseline(ABSENT)
    with pytest.raises(EconomicInterpretationError, match='is not a canonical date'):
        validate_economic_interpretation(
            payload, workspaces=workspace, source_texts=texts, fiscal_scope=scope
        )


@pytest.mark.parametrize('container', [tuple, list])
@pytest.mark.parametrize('count', [0, 1, 3, 5, 8])
def test_fiscal_scope_has_exactly_four_entries(count, container):
    scope = container((FISCAL_SCOPE * 2)[:count])
    assert len(scope) == count
    with pytest.raises(EconomicInterpretationError, match='exactly four dates'):
        _with_fiscal_scope(scope)
    workspace, texts, payload = _baseline(ABSENT)
    with pytest.raises(EconomicInterpretationError, match='exactly four dates'):
        validate_economic_interpretation(
            payload, workspaces=workspace, source_texts=texts, fiscal_scope=scope
        )


@pytest.mark.parametrize('source_clock', [None, '2026-07-29T17:00:00Z'])
@pytest.mark.parametrize('value,refusal', [
    *[(value, 'selection.currentness.state is not an admitted token') for value in (
        ['up_to_date'], {'s': 1}, 1, None, True, '', 'UP_TO_DATE', 'unverified',
    )],
    *[(value, 'selection is not bounded exact JSON data') for value in (
        _Str('up_to_date'), _Str('currentness_unverified'),
    )],
])
def test_currentness_state_is_a_closed_exact_string(value, refusal, source_clock):
    workspace, texts, _payload = _baseline(ABSENT)
    with pytest.raises(EconomicInterpretationError, match=refusal):
        build_economic_interpretation(
            workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE,
            selection={'facts': None, 'currentness': {'state': value, 'source_clock': source_clock}},
            semantic_revision=SEMANTIC_REVISION, code_revision=CODE_REVISION,
        )


def _built_with_currentness(state, source_clock):
    workspace, texts, _payload = _baseline(ABSENT)
    return _build_with(
        workspace, texts, selection={'facts': None, 'currentness': {'state': state, 'source_clock': source_clock}},
    )


def test_currentness_clock_rules_are_exact():
    clock = '2026-07-29T17:00:00Z'
    with pytest.raises(EconomicInterpretationError, match='cannot carry a source clock'):
        _built_with_currentness('currentness_unverified', clock)
    unverified = _built_with_currentness('currentness_unverified', None)['selection']
    assert (unverified['currentness'], unverified['currentness_observed_at']) == ('currentness_unverified', None)
    for state in ('up_to_date', 'newer_source_pending'):
        with pytest.raises(EconomicInterpretationError, match='is not a canonical UTC instant'):
            _built_with_currentness(state, None)
        clocked = _built_with_currentness(state, clock)['selection']
        assert (clocked['currentness'], clocked['currentness_observed_at']) == (state, clock)


class _Int(int):
    pass


@pytest.mark.parametrize('wrap', [_Str, lambda value: _opaque(str, value)])
def test_each_string_parser_decides_by_identity(wrap):
    states = economic_interpretation._CURRENTNESS_STATES
    assert economic_interpretation._parse_token('up_to_date', states, 'state') == 'up_to_date'
    with pytest.raises(EconomicInterpretationError, match='is not an admitted token'):
        economic_interpretation._parse_token(wrap('up_to_date'), states, 'state')
    instant = '2026-07-29T17:00:00Z'
    assert economic_interpretation._parse_instant(instant, 'clock').strftime('%Y-%m-%dT%H:%M:%SZ') == instant
    with pytest.raises(EconomicInterpretationError, match='is not a canonical UTC instant'):
        economic_interpretation._parse_instant(wrap(instant), 'clock')
    assert economic_interpretation._parse_date('2026-06-30', 'date').isoformat() == '2026-06-30'
    with pytest.raises(EconomicInterpretationError, match='is not a canonical date'):
        economic_interpretation._parse_date(wrap('2026-06-30'), 'date')
    assert economic_interpretation._parse_decimal('1.5', 'number') == Decimal('1.5')
    with pytest.raises(EconomicInterpretationError, match='is not a decimal-compatible value'):
        economic_interpretation._parse_decimal(wrap('1.5'), 'number')


@pytest.mark.parametrize('value', [_Int(2), True, 2.0, '2'])
def test_the_precision_parser_decides_by_identity(value):
    assert economic_interpretation._parse_precision(2) == 2
    assert economic_interpretation._parse_precision(None) is None
    with pytest.raises(EconomicInterpretationError, match='precision must be a nonnegative integer or None'):
        economic_interpretation._parse_precision(value)
    with pytest.raises(EconomicInterpretationError, match='precision must be a nonnegative integer or None'):
        economic_interpretation._parse_precision(_opaque(int, 2))


def test_parser_positive_controls_and_clock_text():
    result = build_case_interpretation(
        'identical_inputs',
        selection={'facts': None, 'currentness': {'state': 'up_to_date', 'source_clock': '2026-07-29T17:00:00Z'}},
    )
    assert result['clocks']['source_currentness'] == {
        'en': 'Jul 29, 2026, 17:00 UTC', 'zh': '2026年7月29日 17:00 UTC',
    }
    base = build_case_interpretation('identical_inputs')
    assert base['clocks']['source_accepted'] == {
        'en': 'Jul 29, 2026, 17:00 UTC', 'zh': '2026年7月29日 17:00 UTC',
    }
    assert base['clocks']['fiscal_period'] == {
        'en': 'Quarter ended June 30, 2026', 'zh': '截至2026年6月30日的季度',
    }
    workspace, texts = _case('identical_inputs')
    workspace = copy.deepcopy(workspace)
    workspace['lifecycle']['source_available_at'] = None
    none_clock = build_economic_interpretation(
        workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE,
        selection={'facts': None, 'currentness': None},
        semantic_revision=SEMANTIC_REVISION, code_revision=CODE_REVISION,
    )
    assert none_clock['clocks']['source_accepted'] is None
    base_workspace, base_texts = _case('identical_inputs')
    validate_economic_interpretation(
        result, workspaces=base_workspace, source_texts=base_texts, fiscal_scope=FISCAL_SCOPE,
    )
    validate_economic_interpretation(
        none_clock, workspaces=workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE,
    )


def _opaque(base, *args):
    """A `base` subclass whose type raises when hashed or compared, so only an identity test classifies it."""

    class _Meta(type):
        def __hash__(cls):
            raise RuntimeError('a type test hashed an unchecked type')

        def __eq__(cls, other):
            raise RuntimeError('a type test compared an unchecked type')

    return _Meta('_Opaque', (base,), {})(*args)


@pytest.mark.parametrize('prior', ['0', '-1', '1.52'])
@pytest.mark.parametrize('position', ['current', 'prior', 'uncertainty'])
def test_compare_eps_classifies_numbers_by_identity(position, prior):
    arguments = {'current': '1.64', 'prior': prior, 'uncertainty': '0.01'}
    arguments[position] = _opaque(str, arguments[position])
    with pytest.raises(EconomicInterpretationError, match='decimal-compatible'):
        compare_eps(
            arguments['current'], arguments['prior'], precision=2, uncertainty=arguments['uncertainty']
        )


@pytest.mark.parametrize('base', [tuple, list])
def test_fiscal_scope_container_is_classified_by_identity(base):
    workspace, texts, payload = _baseline(ABSENT)
    _with_fiscal_scope(base(FISCAL_SCOPE))
    validate_economic_interpretation(
        payload, workspaces=workspace, source_texts=texts, fiscal_scope=base(FISCAL_SCOPE)
    )
    scope = _opaque(base, FISCAL_SCOPE)
    with pytest.raises(EconomicInterpretationError, match='exactly four dates'):
        _with_fiscal_scope(scope)
    with pytest.raises(EconomicInterpretationError, match='exactly four dates'):
        validate_economic_interpretation(
            payload, workspaces=workspace, source_texts=texts, fiscal_scope=scope
        )


def test_stored_handle_values_are_exact_strings():
    workspace, texts = _case('identical_inputs')
    baseline = build_case_interpretation('identical_inputs')
    validate_economic_interpretation(
        baseline, workspaces=workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE
    )
    fields = sorted(baseline['observations'][0]['handle'])
    assert fields == ['event_id', 'fact_id', 'workspace_generation_id']
    for field in fields:
        path = ('observations', 0, 'handle', field)
        original = baseline['observations'][0]['handle'][field]
        for wrap in (_Str, lambda value: _opaque(str, value)):
            with pytest.raises(EconomicInterpretationError, match='stored interpretation is not bounded exact JSON'):
                validate_economic_interpretation(
                    _replace_at(baseline, path, wrap(original)),
                    workspaces=workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE,
                )
        for value in (3, None, ['x'], {'a': 'b'}, True, 1.5):
            with pytest.raises(EconomicInterpretationError, match='handle is malformed'):
                validate_economic_interpretation(
                    _replace_at(baseline, path, value),
                    workspaces=workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE,
                )


def test_every_type_test_is_an_identity_test():
    with open(economic_interpretation.__file__, encoding='utf-8') as source:
        tree = ast.parse(source.read())
    identity_tests = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {'isinstance', 'issubclass'}, ast.unparse(node)
        if isinstance(node, ast.Attribute):
            assert node.attr != '__class__', ast.unparse(node)
        if not isinstance(node, ast.Compare):
            continue
        left = node.left
        names_a_type = (
            isinstance(left, ast.Call) and isinstance(left.func, ast.Name) and left.func.id == 'type'
        ) or (isinstance(left, ast.Name) and left.id == 'kind')
        if names_a_type:
            assert all(isinstance(op, (ast.Is, ast.IsNot)) for op in node.ops), ast.unparse(node)
            identity_tests += 1
    assert identity_tests >= IDENTITY_TEST_FLOOR


IDENTITY_TEST_FLOOR = 50


class _Liar(str):
    """Compares equal to anything, so only an identity type test tells it from an exact string."""

    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False

    __hash__ = str.__hash__


class _Raiser:
    """Raises from every operation, so only code that asks it nothing gets past it."""

    def _refuse(self, *args, **kwargs):
        raise RuntimeError('an unchecked value ran its own code')

    __eq__ = __ne__ = __lt__ = __le__ = __gt__ = __ge__ = __hash__ = __bool__ = _refuse
    __len__ = __iter__ = __contains__ = __getitem__ = __str__ = __repr__ = __format__ = _refuse
    __int__ = __float__ = __index__ = __getattr__ = _refuse


class _Twin:
    """Hashes like the key it stands in for and raises when compared, so only code that never looks it up gets past it."""

    def __init__(self, key):
        self._hash = hash(key)

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        raise RuntimeError('an unchecked key ran its own code')


def _replace_at(node, path, value):
    """A copy of `node` with `value` at `path`.  Only the containers along the path are copied."""
    if not path:
        return value
    copied = dict(node) if type(node) is dict else list(node)
    copied[path[0]] = _replace_at(node[path[0]], path[1:], value)
    return tuple(copied) if type(node) is tuple else copied


def _nodes(value, path=()):
    yield path, value
    if type(value) is dict:
        for key, item in value.items():
            yield from _nodes(item, path + (key,))
    elif type(value) is list or type(value) is tuple:
        for index, item in enumerate(value):
            yield from _nodes(item, path + (index,))


def _is_exact_json(value):
    for _path, node in _nodes(value):
        kind = type(node)
        if kind is dict:
            if any(type(key) is not str for key in node):
                return False
        elif kind is float:
            if not math.isfinite(node):
                return False
        elif not (kind is list or kind is str or kind is int or kind is bool or node is None):
            return False
    return True


def _hostile(node):
    """Values no contract admits in place of `node`, as (name, value) pairs."""
    kind = type(node)
    found = [('raiser', _Raiser())]
    if kind is str:
        found += [('str_subclass', _Str(node)), ('opaque_str', _opaque(str, node)), ('liar', _Liar(node))]
    elif kind is dict:
        found.append(('dict_subclass', _opaque(dict, node)))
        if node:
            found.append(('str_subclass_keys', {_Str(key): item for key, item in node.items()}))
            found.append(('liar_keys', {_Liar(key): item for key, item in node.items()}))
            first = next(iter(node))
            found.append(('twin_key', {(_Twin(key) if key is first else key): item for key, item in node.items()}))
    elif kind is list:
        found.append(('list_subclass', _opaque(list, node)))
    elif kind is tuple:
        found.append(('tuple_subclass', _opaque(tuple, node)))
    elif kind is int:
        found.append(('int_subclass', _opaque(int, node)))
    elif kind is float:
        found.append(('float_subclass', _opaque(float, node)))
    return found


def _look_alikes(node):
    """Exact values of another type that compare equal to `node`, as (name, value) pairs."""
    kind = type(node)
    if kind is list:
        return [('tuple_for_list', tuple(node))]
    if kind is bool:
        return [('int_for_bool', int(node))]
    if kind is int:
        return [('float_for_int', float(node))]
    if kind is float and node == int(node):
        return [('int_for_float', int(node))]
    return []


def _outcome(call):
    try:
        result = call()
    except EconomicInterpretationError:
        return 'typed', None
    except Exception as exc:
        return f'escaped {type(exc).__name__}', None
    return 'returned', result


def _where(path, name):
    return '/'.join(str(part) for part in path) + f' <- {name}'


def _build_with(workspace, texts, *, fiscal_scope=FISCAL_SCOPE, selection=None):
    return build_economic_interpretation(
        workspace, source_texts=texts, fiscal_scope=fiscal_scope,
        selection={'facts': None, 'currentness': None} if selection is None else selection,
        semantic_revision=SEMANTIC_REVISION, code_revision=CODE_REVISION,
    )


CLOCKED = {'state': 'up_to_date', 'source_clock': '2026-07-29T17:00:00Z'}


def test_validate_refuses_a_substitute_at_every_stored_position():
    workspace, texts = _case('identical_inputs')
    baseline = build_case_interpretation('identical_inputs', selection={'facts': None, 'currentness': CLOCKED})

    def validate(payload):
        return validate_economic_interpretation(
            payload, workspaces=workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE
        )

    assert _outcome(lambda: validate(baseline))[0] == 'returned'
    assert _is_exact_json(baseline)
    failures, hostile, look_alikes, patterns = [], 0, 0, set()
    for path, node in _nodes(baseline):
        substitutes = _hostile(node)
        hostile += len(substitutes)
        pattern = tuple('*' if type(part) is int else part for part in path)
        if pattern not in patterns:
            patterns.add(pattern)
            substitutes += _look_alikes(node)
            look_alikes += len(_look_alikes(node))
        for name, value in substitutes:
            outcome = _outcome(lambda: validate(_replace_at(baseline, path, value)))[0]
            if outcome != 'typed':
                failures.append(f'{_where(path, name)}: {outcome}')
    assert not failures, failures[:20]
    assert hostile >= 2000 and look_alikes >= 20


def test_build_refuses_a_substitute_at_every_selection_position():
    workspace, texts = _case('identical_inputs')
    rows = validate_selected_facts(workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE)
    handles = _all_handles('identical_inputs')
    by_metric = [
        {'workspace_generation_id': workspace['generation_id'], 'event_id': row['event_id'], 'metric': row['metric']}
        for row in rows[:3]
    ]
    selections = [
        {'facts': None, 'currentness': None},
        {'facts': handles[:3], 'currentness': CLOCKED},
        {'facts': by_metric, 'currentness': {'state': 'currentness_unverified', 'source_clock': None}},
    ]
    failures, checked = [], 0
    for number, selection in enumerate(selections):
        outcome, built = _outcome(lambda: _build_with(workspace, texts, selection=selection))
        assert outcome == 'returned' and built['quality']['supported'] is True
        for path, node in _nodes(selection):
            for name, value in _hostile(node) + _look_alikes(node):
                checked += 1
                candidate = _replace_at(selection, path, value)
                outcome = _outcome(lambda: _build_with(workspace, texts, selection=candidate))[0]
                if outcome != 'typed':
                    failures.append(f'selection {number} {_where(path, name)}: {outcome}')
    assert not failures, failures[:20]
    assert checked >= 100


def test_build_refuses_a_hostile_value_at_every_workspace_position():
    workspace, texts = _case('identical_inputs')
    assert _outcome(lambda: _build_with(workspace, texts))[0] == 'returned'
    failures, checked = [], 0
    for path, node in _nodes(workspace):
        for name, value in _hostile(node):
            checked += 1
            outcome = _outcome(lambda: _build_with(_replace_at(workspace, path, value), texts))[0]
            if outcome != 'typed':
                failures.append(f'{_where(path, name)}: {outcome}')
    assert not failures, failures[:20]
    assert checked >= 2500


def test_build_returns_exact_json_when_a_workspace_list_is_a_tuple():
    workspace, texts = _case('identical_inputs')
    failures, returned, refused = [], 0, 0
    for path, node in _nodes(workspace):
        for name, value in _look_alikes(node) if type(node) is list else []:
            outcome, built = _outcome(lambda: _build_with(_replace_at(workspace, path, value), texts))
            if outcome == 'returned' and _is_exact_json(built):
                returned += 1
            elif outcome == 'typed':
                refused += 1
            else:
                failures.append(f'{_where(path, name)}: {outcome}')
    assert not failures, failures[:20]
    assert returned >= 1 and refused >= 1


def test_every_other_argument_is_refused_when_it_is_not_exact():
    workspace, texts = _case('identical_inputs')
    baseline = build_case_interpretation('identical_inputs')

    def build(**changed):
        arguments = {'workspace': workspace, 'texts': texts, 'fiscal_scope': FISCAL_SCOPE, **changed}
        return _build_with(arguments['workspace'], arguments['texts'], fiscal_scope=arguments['fiscal_scope'])

    def validate(**changed):
        arguments = {'workspaces': workspace, 'source_texts': texts, 'fiscal_scope': FISCAL_SCOPE, **changed}
        return validate_economic_interpretation(baseline, **arguments)

    generation = workspace['generation_id']
    assert _outcome(lambda: validate(workspaces={generation: workspace}))[0] == 'returned'
    assert _outcome(lambda: validate(fiscal_scope=list(FISCAL_SCOPE)))[0] == 'returned'
    calls = []
    for path, node in _nodes(texts):
        for name, value in _hostile(node):
            candidate = _replace_at(texts, path, value)
            calls.append((f'build source_texts {_where(path, name)}', lambda candidate=candidate: build(texts=candidate)))
            calls.append((
                f'validate source_texts {_where(path, name)}',
                lambda candidate=candidate: validate(source_texts=candidate),
            ))
    for path, node in _nodes(FISCAL_SCOPE):
        for name, value in _hostile(node):
            candidate = _replace_at(FISCAL_SCOPE, path, value)
            calls.append((
                f'build fiscal_scope {_where(path, name)}', lambda candidate=candidate: build(fiscal_scope=candidate),
            ))
            calls.append((
                f'validate fiscal_scope {_where(path, name)}',
                lambda candidate=candidate: validate(fiscal_scope=candidate),
            ))
    for name, value in [
        *_hostile(workspace),
        ('str_subclass_generation', {_Str(generation): workspace}),
        ('liar_generation', {_Liar(generation): workspace}),
        ('workspace_subclass', {generation: _opaque(dict, workspace)}),
        ('workspace_raiser', {generation: _Raiser()}),
        ('workspace_list', {generation: [workspace]}),
        ('twin_generation', {_Twin(generation): workspace}),
        ('twin_generation_id', {
            **{key: item for key, item in workspace.items() if key != 'generation_id'},
            _Twin('generation_id'): generation,
        }),
        ('empty', {}),
    ]:
        calls.append((f'validate workspaces <- {name}', lambda value=value: validate(workspaces=value)))
    for name, value in _hostile(workspace):
        calls.append((f'build workspace <- {name}', lambda value=value: build(workspace=value)))
    for name, value in _hostile(baseline):
        calls.append((
            f'validate payload <- {name}',
            lambda value=value: validate_economic_interpretation(
                value, workspaces=workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE
            ),
        ))
    failures = [f'{label}: {outcome}' for label, call in calls for outcome in [_outcome(call)[0]] if outcome != 'typed']
    assert not failures, failures[:20]
    assert len(calls) >= 77


def _exact_eps_value(current, prior, precision):
    exact = (Fraction(Decimal(current)) / Fraction(Decimal(prior)) - 1) * 100
    return format(round(exact, precision), f'.{precision}f')


def test_compare_eps_is_independent_of_the_callers_decimal_context():
    contexts = [
        None,
        Context(prec=5, rounding=ROUND_DOWN),
        Context(prec=50, rounding=ROUND_CEILING),
        Context(prec=9, Emax=999999, Emin=-999999, traps=[]),
    ]
    for context in contexts:
        if context is None:
            assert compare_eps('3.07', '2.93', precision=2)['value'] == '4.78'
            assert compare_eps('1.64', '1.50', precision=2)['value'] == '9.33'
            assert compare_eps('1', '0', precision=2)['reason'] == 'nonpositive_prior'
            with pytest.raises(EconomicInterpretationError, match='EPS growth arithmetic is not defined'):
                compare_eps('1E+999999', '1E-999999', precision=2)
            continue
        with localcontext(context):
            assert compare_eps('3.07', '2.93', precision=2)['value'] == '4.78'
            assert compare_eps('1.64', '1.50', precision=2)['value'] == '9.33'
            assert compare_eps('1', '0', precision=2)['reason'] == 'nonpositive_prior'
            with pytest.raises(EconomicInterpretationError, match='EPS growth arithmetic is not defined'):
                compare_eps('1E+999999', '1E-999999', precision=2)


def _fuzzed_eps_pairs(count):
    generator = random.Random(0xC0FFEE)
    pairs = []
    for _ in range(count):
        current_digits = ''.join(generator.choice('0123456789') for _ in range(generator.randint(1, 30))).lstrip('0') or '1'
        prior_digits = ''.join(generator.choice('0123456789') for _ in range(generator.randint(1, 30))).lstrip('0') or '1'
        current = Decimal(f"{current_digits}E{generator.randint(-10, 10)}")
        prior = Decimal(f"{prior_digits}E{generator.randint(-10, 10)}")
        if prior <= 0:
            prior = abs(prior)
        pairs.append((current, prior, generator.randint(0, 6)))
    return pairs


def test_compare_eps_matches_an_exact_oracle_on_a_fixed_fuzz():
    pairs = _fuzzed_eps_pairs(2500)
    mismatches = []
    for current, prior, precision in pairs:
        try:
            actual = compare_eps(current, prior, precision=precision)['value']
        except EconomicInterpretationError as exc:
            if str(exc) != 'EPS growth arithmetic is not defined':
                raise
            continue
        expected = _exact_eps_value(current, prior, precision)
        if actual != expected:
            mismatches.append((current, prior, precision, actual, expected))
    assert not mismatches, f'{len(pairs)} fuzzed pairs; {len(mismatches)} differed from the oracle; first={mismatches[:3]}'


def test_compare_eps_pins_the_known_default_context_double_rounding():
    # This pair was verified against a copy of the old implementation beside the exact oracle.
    current = '86599450252.21717677831864229'
    prior = '7.86759076908354901062539863897E-8'
    assert compare_eps(current, prior, precision=6)['value'] == '110071116805563916092.505877'
    assert _exact_eps_value(current, prior, 6) == '110071116805563916092.505877'


def test_compare_eps_keeps_guard_digits_below_the_result_precision():
    current = '1.0844295548122237704991540414179152200291362974111E+57'
    prior = '9.4424836711881716913965898127193877E+35'
    assert compare_eps(current, prior, precision=3)['value'] == '114845796145895505333900.479'


def test_compare_eps_still_refuses_a_result_with_too_many_digits():
    with pytest.raises(EconomicInterpretationError, match='EPS growth arithmetic is not defined'):
        compare_eps('1E+40', '1', precision=2)


def test_clock_helpers_format_short_years_with_zero_padding():
    assert economic_interpretation._format_instant(datetime(999, 1, 2, 3, 4, 5)) == '0999-01-02T03:04:05Z'
    assert economic_interpretation._format_date(date(999, 1, 2)) == '0999-01-02'


def test_parsers_accept_short_years_but_keep_the_canonical_forms():
    instant = datetime(999, 1, 2, 3, 4, 5)
    day = date(999, 1, 2)
    assert economic_interpretation._parse_instant('0999-01-02T03:04:05Z', 'x') == instant
    assert economic_interpretation._parse_date('0999-01-02', 'x') == day
    for value in (
        '2026-9-30T00:00:00Z', '2026-09-30T00:00:00+00:00', '2026-02-30T00:00:00Z',
        '0000-01-01T00:00:00Z',
    ):
        with pytest.raises(EconomicInterpretationError):
            economic_interpretation._parse_instant(value, 'x')


def test_compare_eps_refuses_every_unreadable_argument():
    base = {'current': '1.64', 'prior': '1.52', 'precision': 2, 'uncertainty': '0.01'}

    def compare(**changed):
        arguments = {**base, **changed}
        return compare_eps(
            arguments['current'], arguments['prior'],
            precision=arguments['precision'], uncertainty=arguments['uncertainty'],
        )

    assert compare()['value'] == '7.89'
    numbers = [
        *_hostile('1.5'), *_hostile(2)[1:], *_hostile(1.5)[1:],
        ('decimal_subclass', _opaque(Decimal, '1.5')), ('fraction', Fraction(3, 2)), ('bytes', b'1.5'),
        ('list', ['1.5']), ('true', True),
    ]
    calls = [
        (f'{position} <- {name}', lambda position=position, value=value: compare(**{position: value}))
        for position in ('current', 'prior', 'uncertainty') for name, value in numbers
    ]
    calls += [
        (f'precision <- {name}', lambda value=value: compare(precision=value))
        for name, value in [*_hostile(2), ('true', True), ('float', 2.0), ('text', '2'), ('negative', -1)]
    ]
    failures = [f'{label}: {outcome}' for label, call in calls for outcome in [_outcome(call)[0]] if outcome != 'typed']
    assert not failures, failures[:20]
    assert len(calls) >= 39


_UNREADABLE_ERRORS = [
    TypeError, ValueError, ArithmeticError, LookupError, AttributeError,
    KeyError, IndexError, OverflowError, ZeroDivisionError,
]


def _entry_calls():
    workspace, texts, baseline = _baseline(ABSENT)
    return {
        'build': ('_release', lambda: _build_with(workspace, texts)),
        'validate': ('_release', lambda: validate_economic_interpretation(
            baseline, workspaces=workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE
        )),
        'compare_eps': ('_parse_precision', lambda: compare_eps('1.64', '1.52', precision=2)),
    }


@pytest.mark.parametrize('error', _UNREADABLE_ERRORS)
@pytest.mark.parametrize('entry', ['build', 'validate', 'compare_eps'])
def test_each_entry_turns_an_unreadable_value_into_the_typed_refusal(entry, error, monkeypatch):
    patched, call = _entry_calls()[entry]

    def unreadable(*args, **kwargs):
        raise error('a built-in refused a value')

    monkeypatch.setattr(economic_interpretation, patched, unreadable)
    with pytest.raises(EconomicInterpretationError) as caught:
        call()
    assert type(caught.value) is EconomicInterpretationError
    assert str(caught.value) == (
        f'a value has the wrong type or range where the interpretation reads it ({error.__name__})'
    )
    assert type(caught.value.__cause__) is error


@pytest.mark.parametrize('entry', ['build', 'validate', 'compare_eps'])
def test_each_entry_lets_every_other_exception_through(entry, monkeypatch):
    patched, call = _entry_calls()[entry]

    def broken(*args, **kwargs):
        raise RuntimeError('not a wrong-typed value')

    monkeypatch.setattr(economic_interpretation, patched, broken)
    with pytest.raises(RuntimeError, match='not a wrong-typed value'):
        call()


@pytest.mark.parametrize('case,convert,path', [
    (ABSENT, int, ('authority', 'can_rank')),
    (ABSENT, float, ('authority', 'can_rank')),
    (ABSENT, int, ('build', 'deterministic')),
    (ABSENT, int, ('quality', 'supported')),
    (ABSENT, float, ('selection', 'observation_count')),
    ('identical_inputs', int, ('observations', 0, 'value')),
])
def test_replay_compares_types_as_well_as_values(case, convert, path):
    workspace, texts, baseline = _baseline(case)
    original = baseline
    for part in path:
        original = original[part]
    value = convert(original)
    assert value == original and type(value) is not type(original)
    with pytest.raises(EconomicInterpretationError, match='stored interpretation does not replay'):
        validate_economic_interpretation(
            _replace_at(baseline, path, value),
            workspaces=workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE,
        )


def _nested(depth):
    value = 'x'
    for _ in range(depth):
        value = [value]
    return value


def _fan(levels):
    value = ['x']
    for _ in range(levels):
        value = [value, value]
    return value


def _cycle():
    value = []
    value.append(value)
    return value


_UNBOUNDED = [
    ('count', lambda: list(range(100_001))),
    ('nesting', lambda: _nested(40)),
    ('deep_nesting', lambda: _nested(5000)),
    ('shared_fan', lambda: _fan(25)),
    ('cycle', _cycle),
    ('integer', lambda: 10 ** 5000),
    ('integer_at_the_bound', lambda: 10 ** 640),
    ('negative_integer', lambda: -(10 ** 640)),
    ('not_a_number', lambda: float('nan')),
    ('infinity', lambda: float('-inf')),
    ('integer_key', lambda: {1: 'x'}),
    ('tuple', lambda: ('x',)),
    ('fraction', lambda: Fraction(1, 3)),
    ('bytes', lambda: b'x'),
    ('set', lambda: {'x'}),
]


@pytest.mark.parametrize('name', [name for name, _make in _UNBOUNDED])
def test_the_selection_and_a_stored_payload_are_bounded_exact_json(name):
    value = dict(_UNBOUNDED)[name]()
    workspace, texts, baseline = _baseline(ABSENT)
    with pytest.raises(EconomicInterpretationError, match='selection is not bounded exact JSON data'):
        _build_with(workspace, texts, selection={'facts': None, 'currentness': value})
    with pytest.raises(EconomicInterpretationError, match='selection is not bounded exact JSON data'):
        _build_with(workspace, texts, selection={'facts': [value], 'currentness': None})
    with pytest.raises(EconomicInterpretationError, match='stored interpretation is not bounded exact JSON data'):
        validate_economic_interpretation(
            _replace_at(baseline, ('next_evidence',), value),
            workspaces=workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE,
        )


def test_values_at_the_bounds_are_read_and_one_past_them_is_refused():
    workspace, texts, baseline = _baseline(ABSENT)

    def build(currentness=None, facts=None):
        return _build_with(workspace, texts, selection={'facts': facts, 'currentness': currentness})

    def validate(selector_version):
        return validate_economic_interpretation(
            _replace_at(baseline, ('selection', 'selector_version'), selector_version),
            workspaces=workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE,
        )

    for value in (10 ** 640 - 1, -(10 ** 640) + 1, _nested(30)):
        with pytest.raises(EconomicInterpretationError, match='selection.currentness must be a mapping'):
            build(currentness=value)
    with pytest.raises(EconomicInterpretationError, match='selection is not bounded exact JSON data'):
        build(currentness=_nested(31))
    for value in (10 ** 640 - 1, -(10 ** 640) + 1, _nested(29)):
        with pytest.raises(EconomicInterpretationError, match='stored interpretation does not replay'):
            validate(value)
    with pytest.raises(EconomicInterpretationError, match='stored interpretation is not bounded exact JSON data'):
        validate(_nested(30))
    with pytest.raises(EconomicInterpretationError, match='comparisons exceed 24'):
        build(facts=list(range(99_997)))
    with pytest.raises(EconomicInterpretationError, match='selection is not bounded exact JSON data'):
        build(facts=list(range(99_998)))


@pytest.mark.parametrize('value', [
    ('PG',), Fraction(1, 3), float('nan'), float('inf'), {'listings': ('x',)}, [{'rate': Fraction(1, 2)}],
])
def test_a_built_payload_is_exact_json(value):
    workspace, texts, baseline = _baseline(ABSENT)
    assert _is_exact_json(baseline)
    with pytest.raises(EconomicInterpretationError, match='built interpretation is not bounded exact JSON data'):
        _build_with({**workspace, 'issuer': value}, texts)


@pytest.mark.parametrize('value', [None, 5, 1.5, True, ['x'], ('x',), {'a': 1}])
def test_workspace_generation_id_is_an_exact_string(value):
    workspace, texts, _payload = _baseline(ABSENT)
    renamed = _build_with({**workspace, 'generation_id': 'generation_b'}, texts)
    assert {item['handle']['workspace_generation_id'] for item in renamed['observations']} == {'generation_b'}
    with pytest.raises(EconomicInterpretationError, match='workspace generation or event identity is malformed'):
        _build_with({**workspace, 'generation_id': value}, texts)
    without = {key: item for key, item in workspace.items() if key != 'generation_id'}
    with pytest.raises(EconomicInterpretationError, match='workspace generation or event identity is malformed'):
        _build_with(without, texts)


def _with_event_id(workspace, event_id):
    """The workspace under another event id, renamed everywhere Task 1 checks it, so Task 1 still accepts it."""
    facts = []
    for fact in workspace['facts']:
        fact = {**fact, 'event_id': event_id}
        if 'typed_absence' in fact and 'event_id' in fact['typed_absence']:
            fact['typed_absence'] = {**fact['typed_absence'], 'event_id': event_id}
        try:
            definition = economic_observations._definition(fact['metric'])
        except economic_observations.EconomicObservationError:
            facts.append(fact)
            continue
        period = fact['period'] if 'value' in fact else fact['metric']
        fact['fact_id'] = economic_observations._fact_id(event_id, fact['metric'], period, definition.basis)
        facts.append(fact)
    return {**workspace, 'event_id': event_id, 'facts': facts}


@pytest.mark.parametrize('value', [None, 5, 1.5, True])
def test_workspace_event_id_is_an_exact_string(value):
    workspace, texts, _payload = _baseline()
    renamed = _build_with(_with_event_id(workspace, 'evt_other'), texts)
    assert renamed['event_id'] == 'evt_other'
    assert {item['handle']['event_id'] for item in renamed['observations']} == {'evt_other'}
    tampered = _with_event_id(workspace, value)
    assert validate_selected_facts(tampered, source_texts=texts, fiscal_scope=FISCAL_SCOPE)
    with pytest.raises(EconomicInterpretationError, match='workspace generation or event identity is malformed'):
        _build_with(tampered, texts)


@pytest.mark.parametrize('field,value', [
    *[('lifecycle', value) for value in (None, 5, 'x', [], ['x'], 1.5, True)],
    *[('state', value) for value in (5, 1.5, True, ['x'], {'a': 1})],
])
def test_workspace_lifecycle_is_a_mapping_with_a_string_state(field, value):
    workspace, texts, _payload = _baseline(ABSENT)
    lifecycle = value if field == 'lifecycle' else {**workspace['lifecycle'], 'state': value}
    with pytest.raises(EconomicInterpretationError, match='workspace lifecycle is malformed'):
        _build_with({**workspace, 'lifecycle': lifecycle}, texts)


def test_workspace_lifecycle_positive_controls():
    workspace, texts = _case('identical_inputs')
    assert _build_with(workspace, texts)['clocks']['correction'] == 'complete'
    for state in (None, 'corrected'):
        built = _build_with({**workspace, 'lifecycle': {**workspace['lifecycle'], 'state': state}}, texts)
        assert built['clocks']['correction'] == state
    without = {key: item for key, item in workspace.items() if key != 'lifecycle'}
    clocks = _build_with(without, texts)['clocks']
    assert (clocks['correction'], clocks['source_available_at'], clocks['first_observed_at']) == (None, None, None)


@pytest.mark.parametrize('item', [
    {'fact_id': ['x']}, {'fact_id': {'a': 1}}, {'fact_id': 5}, {'fact_id': True}, {'fact_id': 1.5},
    {'metric': ['x']}, {'metric': {'a': 1}}, {'metric': 5}, {'metric': True},
    {'fact_id': 'fact_x', 'metric': 5}, {'fact_id': 5, 'metric': 'pg_diluted_eps'},
])
def test_a_selected_handle_names_its_fact_with_exact_strings(item):
    workspace, texts, _payload = _baseline(ABSENT)
    handle = {'workspace_generation_id': workspace['generation_id'], 'event_id': workspace['event_id'], **item}
    with pytest.raises(EconomicInterpretationError, match='selected fact handle is malformed'):
        _build_with(workspace, texts, selection={'facts': [handle], 'currentness': None})


@pytest.mark.parametrize('facts', ['x', {'a': 1}, 5, True, 1.5])
def test_selected_facts_are_none_or_an_exact_list(facts):
    workspace, texts, payload = _baseline(ABSENT)
    handles = [dict(item['handle']) for item in payload['observations'][:2]]
    assert len(_build_with(workspace, texts, selection={'facts': handles, 'currentness': None})['observations']) == 2
    with pytest.raises(EconomicInterpretationError, match='selection must be a list of native handles'):
        _build_with(workspace, texts, selection={'facts': facts, 'currentness': None})
    with pytest.raises(EconomicInterpretationError, match='selection is not bounded exact JSON data'):
        _build_with(workspace, texts, selection={'facts': tuple(handles), 'currentness': None})


def test_a_selection_selects_at_least_one_observation():
    workspace, texts, payload = _baseline(ABSENT)
    handles = [dict(item['handle']) for item in payload['observations']]
    assert len(_build_with(workspace, texts, selection={'facts': handles[:1], 'currentness': None})['observations']) == 1
    with pytest.raises(EconomicInterpretationError, match='selection selects no observation'):
        _build_with(workspace, texts, selection={'facts': [], 'currentness': None})


@pytest.mark.parametrize('depth', [40, 5000])
def test_a_deep_workspace_value_is_refused(depth):
    workspace, texts, _payload = _baseline(ABSENT)
    with pytest.raises(EconomicInterpretationError, match='native observations are refused'):
        _build_with({**workspace, 'issuer': _nested(depth)}, texts)


def test_validate_resolves_a_workspace_by_its_generation_id():
    base, texts, _payload = _baseline(ABSENT)
    workspace = {**base, 'generation_id': 'generation_b'}
    other = {**base, 'generation_id': 'generation_a'}
    payload = _build_with(workspace, texts)

    def validate(workspaces):
        return validate_economic_interpretation(
            payload, workspaces=workspaces, source_texts=texts, fiscal_scope=FISCAL_SCOPE
        )

    validate(workspace)
    validate({'generation_b': workspace})
    validate({'generation_a': other, 'generation_b': workspace})
    for workspaces in (other, {'generation_a': other}, {'generation_a': workspace}):
        with pytest.raises(EconomicInterpretationError, match='do not resolve to one supplied workspace'):
            validate(workspaces)
    with pytest.raises(EconomicInterpretationError, match='belongs to another workspace generation'):
        validate({'generation_b': other})
    for generation in (None, 5, ['x'], True):
        with pytest.raises(EconomicInterpretationError, match='workspaces must map generation ids to workspaces'):
            validate({**workspace, 'generation_id': generation})
    with pytest.raises(EconomicInterpretationError, match='workspaces must map generation ids to workspaces'):
        validate({'generation_b': workspace, 'note': 'x'})
    bare = _without(workspace, ('schema',))
    built = _build_with(bare, texts)
    for workspaces in (bare, {'generation_b': bare}):
        validate_economic_interpretation(built, workspaces=workspaces, source_texts=texts, fiscal_scope=FISCAL_SCOPE)


_EXACT_SUBSTITUTES = [None, 5, 'x', [], {}]
# Task 1 admits more than JSON parses to: a tuple, a Fraction, and any of its types as a mapping key.
_ADMITTED_VALUES = [1.5, True, ('x',), Fraction(1, 2)]
_ADMITTED_KEYS = [None, 5, 1.5, True, ('a',), Fraction(1, 2)]


def _without(node, path):
    """A copy of `node` without the entry at `path`."""
    if len(path) > 1:
        copied = dict(node) if type(node) is dict else list(node)
        copied[path[0]] = _without(node[path[0]], path[1:])
        return copied
    if type(node) is dict:
        return {key: item for key, item in node.items() if key != path[0]}
    return [item for index, item in enumerate(node) if index != path[0]]


def _edits(tree, substitutes=_EXACT_SUBSTITUTES):
    """`tree` changed at one position, as (label, tree) pairs: each substitute put there, and the entry removed."""
    for path, _node in _nodes(tree):
        if path:
            for value in substitutes:
                yield _where(path, repr(value)), _replace_at(tree, path, value)
            yield _where(path, 'removed'), _without(tree, path)


def _key_edits(tree):
    """`tree` with one more key in one of its mappings, as (label, tree) pairs: each key that is not a string."""
    for path, node in _nodes(tree):
        if type(node) is dict:
            for key in _ADMITTED_KEYS:
                yield _where(path, f'key {key!r}'), _replace_at(tree, path, {**node, key: None})


def test_whatever_build_returns_replays():
    base, texts, _payload = _baseline(ABSENT)
    workspace = {**base, 'generation_id': 'generation_b'}
    handles = [dict(item['handle']) for item in _build_with(workspace, texts)['observations']]
    selection = {'facts': handles[:2], 'currentness': CLOCKED}
    valued, valued_texts, _payload = _baseline()
    valued = {**valued, 'generation_id': 'generation_b'}
    everything = {'facts': None, 'currentness': CLOCKED}
    calls = [
        ('nothing changed', workspace, texts, selection),
        ('a release with values', valued, valued_texts, everything),
        ('a release with values, schema removed', _without(valued, ('schema',)), valued_texts, everything),
    ]
    calls += [
        (f'workspace {label}', edited, texts, selection)
        for label, edited in _edits(workspace, _EXACT_SUBSTITUTES + _ADMITTED_VALUES)
    ]
    keyed = [(f'workspace {label}', edited, texts, selection) for label, edited in _key_edits(workspace)]
    calls += keyed
    calls += [(f'selection {label}', workspace, texts, edited) for label, edited in _edits(selection)]
    keyed_labels = {call[0] for call in keyed}
    failures, replayed, refused, keyed_replays = [], 0, 0, 0
    for label, candidate, source_texts, selected in calls:
        outcome, built = _outcome(lambda: _build_with(candidate, source_texts, selection=selected))
        if outcome == 'typed':
            refused += 1
            continue
        if outcome != 'returned' or not _is_exact_json(built) or built['quality']['supported'] is not True:
            failures.append(f'{label}: {outcome}')
            continue
        for form, workspaces in (('one workspace', candidate), ('a mapping', {candidate['generation_id']: candidate})):
            replay = _outcome(lambda: validate_economic_interpretation(
                built, workspaces=workspaces, source_texts=source_texts, fiscal_scope=FISCAL_SCOPE
            ))[0]
            if replay != 'returned':
                failures.append(f'{label}: built, then validate as {form} {replay}')
        replayed += 1
        keyed_replays += label in keyed_labels
    assert not failures, failures[:20]
    assert replayed >= 2000 and refused >= 3000, (replayed, refused)
    assert keyed_replays >= 150, (keyed_replays, len(keyed))


@pytest.mark.parametrize('key', _ADMITTED_KEYS, ids=['none', 'int', 'float', 'bool', 'tuple', 'fraction'])
def test_validate_accepts_a_workspace_a_build_accepts_whatever_its_keys(key):
    base, texts, _payload = _baseline(ABSENT)
    workspace = {**base, 'generation_id': 'generation_b', key: None}
    built = _build_with(workspace, texts)
    assert built['quality']['supported'] is True and _is_exact_json(built)
    for workspaces in (workspace, {'generation_b': workspace}):
        validate_economic_interpretation(built, workspaces=workspaces, source_texts=texts, fiscal_scope=FISCAL_SCOPE)


@pytest.mark.parametrize('kind', ['none', 'int', 'list', 'tuple', 'subclass', 'liar', 'opaque', 'raiser'])
def test_unavailable_payload_hides_both_revisions_when_both_are_inexact(kind):
    hostile = {
        'none': None, 'int': 5, 'list': ['x'], 'tuple': ('x',), 'subclass': _Str('wrong'),
        'liar': _Liar('x'), 'opaque': _opaque(str, 'wrong'), 'raiser': _Raiser(),
    }[kind]
    workspace, texts, _payload = _baseline(ABSENT)
    payload = build_economic_interpretation(
        workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE,
        selection={'facts': None, 'currentness': None},
        semantic_revision=hostile, code_revision=hostile,
    )
    assert payload['quality'] == {
        'supported': False, 'state': 'unavailable', 'reason': 'unsupported interpretation version',
    }
    assert payload['build']['semantic_revision'] is None
    assert payload['build']['code_revision'] is None
    assert _is_exact_json(payload)


def test_validate_ignores_nested_key_order_but_requires_exact_top_level_order():
    workspace, texts, payload = _baseline(ABSENT)
    nested = {key: value for key, value in reversed(payload['quality'].items())}
    reordered = {**payload, 'quality': nested}
    validate_economic_interpretation(
        reordered, workspaces=workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE
    )
    reversed_payload = {key: payload[key] for key in reversed(payload)}
    with pytest.raises(EconomicInterpretationError, match='interpretation top-level keys are not exact'):
        validate_economic_interpretation(
            reversed_payload, workspaces=workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE
        )


def test_validate_refuses_empty_workspaces_with_the_exact_message():
    workspace, texts, payload = _baseline(ABSENT)
    with pytest.raises(
        EconomicInterpretationError,
        match=r'^workspaces must map generation ids to workspaces$',
    ):
        validate_economic_interpretation(
            payload, workspaces={}, source_texts=texts, fiscal_scope=FISCAL_SCOPE
        )


@pytest.mark.parametrize('field', ['semantic_revision', 'code_revision'])
@pytest.mark.parametrize('kind', ['none', 'int', 'list', 'tuple', 'subclass', 'liar', 'opaque', 'raiser'])
def test_unavailable_payload_echoes_only_an_exact_string_revision(kind, field):
    revisions = {'semantic_revision': SEMANTIC_REVISION, 'code_revision': CODE_REVISION}
    other = next(name for name in revisions if name != field)
    revisions[field] = {
        'none': None, 'int': 5, 'list': ['x'], 'tuple': ('x',), 'subclass': _Str(revisions[field]),
        'liar': _Liar('x'), 'opaque': _opaque(str, revisions[field]), 'raiser': _Raiser(),
    }[kind]
    workspace, texts, _payload = _baseline(ABSENT)
    payload = build_economic_interpretation(
        workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE,
        selection={'facts': None, 'currentness': None}, **revisions,
    )
    assert payload['quality'] == {
        'supported': False, 'state': 'unavailable', 'reason': 'unsupported interpretation version',
    }
    assert payload['build'][field] is None
    assert payload['build'][other] == revisions[other]
    assert _is_exact_json(payload)
