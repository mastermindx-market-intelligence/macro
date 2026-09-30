from decimal import Decimal
import copy
import hashlib
import json
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
from engine.company_intelligence.economic_observations import validate_selected_facts


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
    assert missing['pg_reported_eps_growth_pct'] == 'no_span_addressable_evidence'


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


def test_spec_strings_are_exact():
    result = build_case_interpretation('identical_inputs')
    labels = {item['metric']: item['label'] for item in result['observations']}
    assert labels['pg_reported_sales_growth_pct'] == {
        'en': 'Reported sales growth', 'zh': '报告销售额增长'
    }
    assert labels['pg_organic_volume_growth_pct'] == {
        'en': 'Organic volume growth', 'zh': '有机销量增长'
    }
    assert labels['pg_core_eps'] == {'en': 'Core EPS', 'zh': '核心每股收益'}
    assert labels['pg_beauty_organic_sales_growth_pct'] == {'en': 'Beauty', 'zh': 'Beauty'}
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
    with pytest.raises(EconomicInterpretationError):
        compare_eps(current, prior, precision=40 if current == '1.64' else 2)


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
    payload = build_case_interpretation('identical_inputs')
    workspace, texts = _case('identical_inputs')
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
    earnings = build_case_interpretation('unlocated_outcome')['missing_context']
    assert any(value['subject'] == 'pg_reported_eps_growth_pct' and value['owner'] == 'earnings' for value in earnings)


def test_unforged_outcome_and_demand_absence_come_from_task_one():
    unlocated = build_case_interpretation('unlocated_outcome')
    row = next(item for item in unlocated['observations'] if item['metric'] == 'pg_reported_eps_growth_pct')
    assert row['typed_absence']['reason'] == 'no_span_addressable_evidence'
    assert row['typed_absence']['detail'] == 'This literal growth fact is not separately disclosed by the selected source.'
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


class _Str(str):
    pass


def _call_with_currentness(value):
    build_case_interpretation(
        'identical_inputs',
        selection={'facts': None, 'currentness': {'state': 'up_to_date', 'source_clock': value}},
    )


def _validated_with_observed_at(value):
    payload = build_case_interpretation(
        'identical_inputs',
        selection={'facts': None, 'currentness': {'state': 'up_to_date', 'source_clock': '2026-07-29T17:00:00Z'}},
    )
    workspace, texts = _case('identical_inputs')
    payload['selection']['currentness_observed_at'] = value
    with pytest.raises(EconomicInterpretationError):
        validate_economic_interpretation(
            payload, workspaces=workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE
        )


def _built_with_lifecycle(field, value):
    workspace, texts = _case('identical_inputs')
    workspace = copy.deepcopy(workspace)
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
    workspace, texts = _case('identical_inputs')
    build_economic_interpretation(
        workspace, source_texts=texts, fiscal_scope=value,
        selection={'facts': None, 'currentness': None},
        semantic_revision=SEMANTIC_REVISION, code_revision=CODE_REVISION,
    )


@pytest.mark.parametrize('position,value', [
    *[(position, value) for position in range(4) for value in _DATE_VALUES],
    *[(position, value) for position in range(4) for value in (FISCAL_SCOPE[:3], FISCAL_SCOPE[:5])],
])
def test_dates_are_parsed_in_build_and_validate(position, value):
    scope = list(FISCAL_SCOPE)
    if isinstance(value, (list, tuple)) and len(value) != 4:
        scope = value
    else:
        scope[position] = value
    with pytest.raises(EconomicInterpretationError):
        _with_fiscal_scope(scope)
    payload = build_case_interpretation('identical_inputs')
    workspace, texts = _case('identical_inputs')
    with pytest.raises(EconomicInterpretationError):
        validate_economic_interpretation(
            payload, workspaces=workspace, source_texts=texts, fiscal_scope=scope
        )


@pytest.mark.parametrize('value', [
    ['up_to_date'], {'s': 1}, 1, None, 'UP_TO_DATE', 'unverified',
    _Str('up_to_date'),
])
def test_currentness_state_is_a_closed_exact_string(value):
    workspace, texts = _case('identical_inputs')
    with pytest.raises(EconomicInterpretationError):
        build_economic_interpretation(
            workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE,
            selection={'facts': None, 'currentness': {'state': value, 'source_clock': None}},
            semantic_revision=SEMANTIC_REVISION, code_revision=CODE_REVISION,
        )


def test_currentness_clock_rules_are_exact():
    with pytest.raises(EconomicInterpretationError):
        _call_with_currentness({'state': 'currentness_unverified', 'source_clock': '2026-07-29T17:00:00Z'})
    with pytest.raises(EconomicInterpretationError):
        _call_with_currentness({'state': 'up_to_date', 'source_clock': None})


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
