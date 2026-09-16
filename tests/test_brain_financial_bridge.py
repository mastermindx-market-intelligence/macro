"""R2A: conditional arithmetic, not live model or investment-performance proof."""
from copy import deepcopy
from decimal import Decimal
import importlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import pytest

MODULE = 'engine.neuralweb.brain_financial_bridge'
ROOT = Path(__file__).resolve().parents[1]


def analyze(payload):
    assert importlib.util.find_spec(MODULE) is not None, 'R2A financial bridge is not implemented'
    return importlib.import_module(MODULE).analyze_financial_bridge(payload)


def scenario():
    return {
        'basis': 'supplied_scenario', 'currency': 'USD', 'amount_scale': 'millions',
        'prior': {'period_months': 12, 'revenue': 100, 'gross_margin_pct': 30, 'operating_expenses': 20},
        'current': {'period_months': 12, 'revenue': 110, 'gross_margin_pct': 25,
                    'operating_expenses': 20, 'depreciation_amortization': 0,
                    'cash_interest': 0, 'cash_taxes': 0, 'working_capital_increase': 8,
                    'capital_expenditures': 5, 'other_operating_cash_adjustments': 0},
    }


def value(result, key):
    v = result['calculations'][key]['value']
    return None if v is None else Decimal(v)


def test_flagship_case_closes_financial_chain_without_fabricating_prior_cash():
    r = analyze(scenario())
    assert r['schema'] == 'brain.financial_bridge.v1'
    assert r['status'] == 'partial'
    assert r['input_provenance'] == 'caller_supplied_unverified'
    assert r['authority'] == 'analysis_only'
    for k, v in {'prior.gross_profit':'30','current.gross_profit':'27.5',
                 'prior.operating_profit':'10','current.operating_profit':'7.5',
                 'current.simplified_operating_cash':'-0.5','current.cash_after_capex':'-5.5',
                 'change.revenue_pct':'10','change.operating_profit_pct':'-25',
                 'bridge.gross_profit_sales_effect':'3','bridge.gross_profit_margin_effect':'-5.5'}.items():
        assert value(r,k) == Decimal(v), k
    assert value(r,'prior.simplified_operating_cash') is None
    assert value(r,'change.cash_after_capex') is None
    assert 'prior.working_capital_increase' in r['calculations']['change.cash_after_capex']['missing_inputs']
    assert 'revenue_up_gross_profit_down' in r['arithmetic_observations']
    assert 'current_profit_positive_operating_cash_negative' in r['arithmetic_observations']


def test_earnings_growth_can_coexist_with_lower_conditional_price():
    p=scenario()
    p['prior'].update(eps=5, earnings_multiple=20)
    p['current'].update(eps=6, earnings_multiple=15)
    r=analyze(p)
    assert value(r,'prior.implied_price') == 100
    assert value(r,'current.implied_price') == 90
    assert value(r,'change.eps_pct') == 20
    assert value(r,'change.implied_price_pct') == -10
    assert value(r,'bridge.price_earnings_effect') == 20
    assert value(r,'bridge.price_multiple_effect') == -30
    assert 'eps_up_implied_price_down' in r['arithmetic_observations']
    assert r['calculations']['current.implied_price']['unit'] == 'USD/share'
    assert not any(k in r for k in ('target_price','probability','score','rank','trade'))


def test_missing_cash_adjustment_is_not_assumed_zero():
    p=scenario(); del p['current']['cash_taxes']
    r=analyze(p)
    assert value(r,'current.operating_profit') == Decimal('7.5')
    assert value(r,'current.simplified_operating_cash') is None
    assert r['calculations']['current.simplified_operating_cash']['missing_inputs'] == ['current.cash_taxes']
    p['current']['cash_taxes']=0
    assert value(analyze(p),'current.simplified_operating_cash') == Decimal('-.5')


@pytest.mark.parametrize('bad',[True,False,'NaN','Infinity',float('nan'),float('inf'),{},[],10**40,'1'*120,'__import__("os")'])
def test_bad_numeric_inputs_fail_closed_and_are_not_echoed(bad):
    p=scenario(); p['current']['revenue']=bad
    r=analyze(p)
    assert r['status']=='invalid_request'
    assert r['calculations']=={}
    assert r['errors']==['current.revenue:invalid_number']
    json.dumps(r,allow_nan=False)
    assert '__import__' not in json.dumps(r)


@pytest.mark.parametrize('bad',[True,12.0,'12',0,25,None])
def test_period_length_requires_literal_bounded_integer(bad):
    p=scenario(); p['current']['period_months']=bad
    assert analyze(p)['status']=='invalid_request'


def test_mixed_periods_and_unknown_units_or_fields_are_rejected():
    p=scenario(); p['prior']['period_months']=3
    assert 'periods:not_comparable' in analyze(p)['errors']
    p=scenario(); p['current']['currency']='CNY'
    assert analyze(p)['status']=='invalid_request'
    p=scenario(); p['portfolio']='private holdings must never be echoed'
    r=analyze(p); assert r['status']=='invalid_request'
    assert 'private holdings' not in json.dumps(r)


def test_quarterly_eps_is_not_silently_annualized():
    p=scenario()
    for period in ('prior','current'):
        p[period].update(period_months=3,eps=5,earnings_multiple=20)
    r=analyze(p)
    assert value(r,'current.implied_price') is None
    assert r['calculations']['current.implied_price']['reason']=='annual_eps_required'
    assert value(r,'current.operating_profit') == Decimal('7.5')


@pytest.mark.parametrize('prior',[0,-5])
def test_growth_percentage_is_not_claimed_on_nonpositive_base(prior):
    p=scenario(); p['prior'].update(revenue=100,gross_margin_pct=20,operating_expenses=20-prior)
    r=analyze(p)
    assert value(r,'change.operating_profit') == Decimal('7.5')-prior
    assert value(r,'change.operating_profit_pct') is None
    assert r['calculations']['change.operating_profit_pct']['reason']=='nonpositive_base'


def test_scale_change_preserves_ratios_and_per_share_values():
    p=scenario(); p['prior'].update(eps=5,earnings_multiple=20); p['current'].update(eps=6,earnings_multiple=15)
    a=analyze(p); p['amount_scale']='thousands'
    money={'revenue','operating_expenses','depreciation_amortization','cash_interest','cash_taxes',
           'working_capital_increase','capital_expenditures','other_operating_cash_adjustments'}
    for period in ('prior','current'):
        for k in money & set(p[period]): p[period][k]*=1000
    b=analyze(p)
    assert value(a,'change.revenue_pct')==value(b,'change.revenue_pct')
    assert value(a,'current.implied_price')==value(b,'current.implied_price')
    assert value(b,'current.gross_profit')==1000*value(a,'current.gross_profit')


def test_call_is_deterministic_does_not_mutate_input_or_decimal_context():
    from decimal import getcontext
    p=scenario(); before=deepcopy(p); context=getcontext().copy()
    a=analyze(p); b=analyze(p)
    assert a==b and p==before
    assert getcontext().prec==context.prec and getcontext().rounding==context.rounding
    assert len(json.dumps(a)) < 20000
    for cell in a['calculations'].values():
        assert isinstance(cell['formula'],str) and cell['inputs']
        assert cell['value'] is None or isinstance(cell['value'],str)


def test_decimal_inputs_remain_decimal_not_binary_float_artifacts():
    p=scenario(); p['current'].update(revenue='0.1',gross_margin_pct='30',operating_expenses='0.02')
    r=analyze(p)
    assert r['calculations']['current.gross_profit']['value']=='0.03'
    assert r['calculations']['current.operating_profit']['value']=='0.01'


def cli(raw):
    return subprocess.run([sys.executable,'-m','scripts.analyze_financial_bridge'],
                          cwd=ROOT,input=raw,text=True,capture_output=True,timeout=15)


def test_cli_consumer_emits_one_json_result_for_the_real_flagship_case():
    p=cli(json.dumps(scenario()))
    assert p.returncode==0,p.stderr
    r=json.loads(p.stdout)
    assert value(r,'current.cash_after_capex')==Decimal('-5.5')
    assert p.stderr=='' and len(p.stdout.splitlines())==1


@pytest.mark.parametrize('raw',['{bad json','{"basis":"supplied_scenario","basis":"verified_facts"}',
                              '{"revenue":NaN}','x'*32769])
def test_cli_rejects_malformed_duplicate_nonfinite_and_oversize_input(raw):
    p=cli(raw)
    assert p.returncode==2,p.stderr
    r=json.loads(p.stdout)
    assert r['status']=='invalid_request' and r['calculations']=={}
    assert len(p.stdout)<1000


def test_input_receipt_preserves_all_accepted_decimal_places():
    p=scenario(); p['current']['revenue']='0.123456789123'
    r=analyze(p)
    assert r['inputs']['current.revenue']=='0.123456789123'


def test_caller_decimal_traps_cannot_change_a_result():
    from decimal import Inexact, Rounded, localcontext
    expected=analyze(scenario())
    with localcontext() as context:
        context.prec=4
        context.traps[Inexact]=True
        context.traps[Rounded]=True
        assert analyze(scenario())==expected


def test_small_negative_cash_is_not_rounded_into_a_false_zero():
    p=scenario()
    p['current'].update(revenue='0.000000000001',gross_margin_pct=1,
                        operating_expenses='0.000000000001',working_capital_increase=0,
                        capital_expenditures=0)
    r=analyze(p)
    assert value(r,'current.operating_profit') < 0
    assert value(r,'current.simplified_operating_cash') < 0
    assert value(r,'current.cash_after_capex') < 0
    for cell in r['calculations'].values():
        if cell['value'] is not None:
            assert isinstance(cell['rounded'],bool)
