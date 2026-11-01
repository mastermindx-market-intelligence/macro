"""Bounded public interpretation regressions; explicit fixture facts only."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from engine.government_revenue import program_theme_disclosure as disclosure


def resolved():
    prefix = 'evt_cik0000936468_2026q2_results:fleet_rms_'
    values = dict(sales=4354, sales_prior=3995, operating_profit=437,
                  operating_profit_prior=-172, margin=10, margin_prior=-4.3)
    facts = [dict(fact_id=prefix + metric, value=value,
                  period='2025Q2' if metric.endswith('_prior') else '2026Q2',
                  unit='percent' if metric.startswith('margin') else 'USD_million',
                  accounting_basis='issuer_reported_segment:Rotary and Mission Systems:reported',
                  owner_ref='fixture:same-replayed-RMS-document')
             for metric, value in values.items()]
    owner = SimpleNamespace(payload=lambda: dict(profiles=[dict(
        ticker_display='LMT', axes=dict(economics=dict(facts=facts)))]))
    rows = [('economics', 'defense_economics', f, owner) for f in facts]
    rows.append(('funding_stage', 'fms', dict(case_key='fms:transmittal:25-104',
                                            stage='congressional_notification'), None))
    return rows


def test_fleet_reported_comparison_keeps_prior_loss_and_scope():
    story = disclosure._theme_economic_story('fleet_sustainment_upgrades', resolved())
    assert 'operating loss' in story[0] and 'operating profit' in story[0]
    assert 'percentage profit growth' in story[0]
    assert 'F-100 revenue' in story[0] and 'cash generation' in story[0]
    assert '营业亏损' in story[1] and '营业利润' in story[1]
    assert story[2:] == disclosure._THEME_CASES['fleet_sustainment_upgrades'][2:]


def test_fleet_baselines_display_both_quarters_without_losing_negative_signs():
    en, zh = disclosure._reported_baselines(resolved())
    for literal in ('4354', '3995', '437', '-172', '10', '-4.3', '2026Q2', '2025Q2'):
        assert literal in en and literal in zh
    assert 'Rotary and Mission Systems' in en


@pytest.mark.parametrize('mutation', ['missing', 'duplicate', 'period', 'unit', 'basis', 'owner', 'bool', 'nan'])
def test_fleet_comparison_refuses_incomplete_or_incompatible_operands(mutation):
    rows = deepcopy(resolved())
    if mutation == 'missing':
        rows.pop(0)
    elif mutation == 'duplicate':
        rows.insert(0, rows[0])
    else:
        field, value = {
            'period': ('period', '2026Q1'), 'unit': ('unit', 'USD'),
            'basis': ('accounting_basis', 'consolidated'), 'owner': ('owner_ref', 'another-document'),
            'bool': ('value', True), 'nan': ('value', float('nan')),
        }[mutation]
        rows[0][2][field] = value
    story = disclosure._theme_economic_story('fleet_sustainment_upgrades', rows)
    assert story == disclosure._THEME_CASES['fleet_sustainment_upgrades']


def test_financial_comparison_does_not_replace_notification_stage_gate():
    assert disclosure._theme_economic_story('fleet_sustainment_upgrades', resolved()[:-1]) is None
