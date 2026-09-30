from decimal import Decimal

import pytest

from engine.earnings_narrative import economic_interpretation
from engine.earnings_narrative.economic_interpretation import (
    AUTHORITY_KEYS,
    TOP_LEVEL_KEYS,
    EconomicInterpretationError,
    build_economic_interpretation,
    compare_eps,
    validate_economic_interpretation,
)
from tests.earnings_economic_fixtures import FISCAL_SCOPE
from tests.earnings_economic_interpretation_fixtures import _case, build_case_interpretation


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
    result = compare_eps(Decimal('3.07'), Decimal('2.00'), precision=2)
    built = build_case_interpretation('uncertain_prior_eps')['comparisons'][0]['result']
    assert built['reason'] == result['reason'] == 'uncertainty_interval_touches_zero'
    assert result == {
        'state': 'not_comparable', 'value': None,
        'reason': 'uncertainty_interval_touches_zero',
        'formula': '(current / prior - 1) * 100',
    }


def test_optional_absence_leaves_supported_explanation():
    result = build_case_interpretation('segment_and_reconciliation_absent')
    assert result['quality']['supported'] is True
    assert {'core_reconciliation', 'segment_organic_sales'} <= {x['subject'] for x in result['missing_context']}
    assert 'incomplete_margin_to_cash_bridge' in {x['rule_id'] for x in result['findings']}


def test_twenty_five_comparison_rows_are_refused():
    with pytest.raises(EconomicInterpretationError, match='comparisons exceed 24'):
        build_case_interpretation('twenty_five_comparisons')


def test_fake_fact_selector_is_refused():
    with pytest.raises(EconomicInterpretationError, match='selected fact handle is absent'):
        build_case_interpretation('fake_fact_selector')


def test_changed_code_version_preserves_native_clocks():
    baseline = build_case_interpretation('changed_code_version')
    changed = build_case_interpretation('changed_code_version', code_revision='synthetic-code-revision-v2')
    assert changed['interpretation_id'] != baseline['interpretation_id']
    assert changed['clocks'] == baseline['clocks']


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
    with pytest.raises(EconomicInterpretationError, match='stored comparisons does not replay'):
        validate_economic_interpretation(payload, workspaces=workspace, source_texts=texts, fiscal_scope=FISCAL_SCOPE)


def test_tampered_stored_result_fails_trusted_validation():
    payload = build_case_interpretation('identical_inputs')
    payload['comparisons'][0]['result']['value'] = '99.99'
    workspace, texts = _case('identical_inputs')
    with pytest.raises(EconomicInterpretationError, match='stored comparisons does not replay'):
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
            selection=None, semantic_revision='synthetic-semantic-revision-v1',
            code_revision='synthetic-code-revision-v1',
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
