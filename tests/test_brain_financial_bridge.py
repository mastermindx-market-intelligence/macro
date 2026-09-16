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


def test_cli_accepts_finite_json_scientific_number_not_an_expression():
    raw=json.dumps(scenario()).replace('"revenue": 100','"revenue": 1e2')
    p=cli(raw)
    assert p.returncode==0,p.stdout
    assert value(json.loads(p.stdout),'prior.gross_profit')==Decimal('30')


def test_empty_and_complete_scenarios_report_their_actual_calculation_state():
    p={'basis':'supplied_scenario','currency':'USD','amount_scale':'units',
       'prior':{'period_months':12},'current':{'period_months':12}}
    assert analyze(p)['status']=='unavailable'
    p=scenario()
    for period in ('prior','current'):
        for field in ('depreciation_amortization','cash_interest','cash_taxes',
                      'working_capital_increase','capital_expenditures','other_operating_cash_adjustments'):
            p[period].setdefault(field,0)
        p[period].update(eps=5,earnings_multiple=20)
    assert analyze(p)['status']=='complete'


def test_pure_calculator_never_opens_files_network_or_evaluates_code(monkeypatch):
    import builtins
    import socket
    module=importlib.import_module(MODULE)
    def forbidden(*args,**kwargs):
        raise AssertionError('calculator attempted an effect')
    monkeypatch.setattr(builtins,'open',forbidden)
    monkeypatch.setattr(builtins,'eval',forbidden)
    monkeypatch.setattr(socket,'socket',forbidden)
    assert module.analyze_financial_bridge(scenario())['status']=='partial'


def test_randomized_bridge_terms_reconcile_to_independent_arithmetic():
    import random
    rng=random.Random(260916)
    for _ in range(400):
        p=scenario()
        for period in ('prior','current'):
            p[period].update(revenue=rng.randint(1,100000),gross_margin_pct=rng.randint(-20,90),
                             operating_expenses=rng.randint(0,10000),eps=rng.randint(1,100),
                             earnings_multiple=rng.randint(1,80))
        r=analyze(p)
        a,b=p['prior'],p['current']
        expected=(Decimal(b['revenue'])*b['gross_margin_pct']-Decimal(a['revenue'])*a['gross_margin_pct'])/100
        actual=value(r,'bridge.gross_profit_sales_effect')+value(r,'bridge.gross_profit_margin_effect')
        assert actual==expected==value(r,'change.gross_profit')
        assert actual+value(r,'bridge.operating_expense_effect')==value(r,'change.operating_profit')
        earnings_effect=(b['eps']-a['eps'])*a['earnings_multiple']
        multiple_effect=b['eps']*(b['earnings_multiple']-a['earnings_multiple'])
        assert value(r,'bridge.price_earnings_effect')==earnings_effect
        assert value(r,'bridge.price_multiple_effect')==multiple_effect
        assert earnings_effect+multiple_effect==value(r,'change.implied_price')


def test_process_default_decimal_policy_cannot_change_a_result():
    from decimal import DefaultContext, Inexact, Rounded
    expected=analyze(scenario())
    previous=DefaultContext.copy()
    try:
        DefaultContext.traps[Inexact]=True
        DefaultContext.traps[Rounded]=True
        DefaultContext.Emax=4
        DefaultContext.Emin=-4
        DefaultContext.clamp=1
        assert analyze(scenario())==expected
    finally:
        DefaultContext.traps=previous.traps
        DefaultContext.Emax=previous.Emax
        DefaultContext.Emin=previous.Emin
        DefaultContext.clamp=previous.clamp


def test_missing_price_basis_is_in_the_decomposition_dependency_receipt():
    p=scenario()
    p['prior'].update(eps=5,earnings_multiple=20)
    p['current'].update(eps=6)
    r=analyze(p)
    for name in ('bridge.price_earnings_effect','bridge.price_multiple_effect'):
        cell=r['calculations'][name]
        assert cell['value'] is None
        assert cell['missing_inputs']==['current.earnings_multiple']
        assert cell['requires']==['prior.implied_price','current.implied_price']


def test_native_tool_schema_is_closed_and_describes_unverified_arguments():
    import jsonschema
    module=importlib.import_module(MODULE)
    factory=getattr(module,'financial_bridge_tool_schema',None)
    assert callable(factory), 'Financial bridge has no native Brain tool contract'
    tool=factory()
    assert tool['name']=='calculate_financial_bridge'
    assert 'not verified facts' in tool['description']
    assert 'Do not invent' in tool['description']
    schema=tool['input_schema']
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(scenario(),schema)
    assert schema['additionalProperties'] is False
    assert schema['properties']['prior']['additionalProperties'] is False
    assert schema['properties']['current']['additionalProperties'] is False
    for bad in (True,[],{},'os.system("echo bad")'):
        p=scenario(); p['current']['revenue']=bad
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(p,schema)
    changed=factory(); changed['input_schema']['required'].clear()
    assert factory()['input_schema']['required']


def test_existing_brain_result_transport_preserves_parallel_math_and_errors():
    """Actual batch/result functions, simulated routing. NOT registry/live proof."""
    from types import SimpleNamespace
    from engine.neuralweb import brain_gateway as gateway
    module=importlib.import_module(MODULE)
    one=scenario(); two=scenario(); two['current']['revenue']=120
    invalid=scenario(); invalid['portfolio']='PRIVATE_MARKER_MUST_NOT_LEAK'
    requests=[one,two,invalid]
    blocks=[SimpleNamespace(name='calculate_financial_bridge',input=p,id=str(i))
            for i,p in enumerate(requests)]
    def dispatch(name,payload):
        assert name=='calculate_financial_bridge'
        return module.analyze_financial_bridge(payload)
    results=gateway._run_tool_blocks(
        blocks,lambda block: gateway._run_tool_block(block,dispatch))
    expected=[module.analyze_financial_bridge(p) for p in requests]
    assert results==expected
    assert value(results[0],'current.operating_profit')==Decimal('7.5')
    assert value(results[1],'current.operating_profit')==Decimal('10')
    assert results[2]['status']=='invalid_request'
    for result in results:
        transported=gateway._model_visible_tool_result('calculate_financial_bridge',result)
        assert json.loads(json.dumps(transported,allow_nan=False))==result
        assert 'PRIVATE_MARKER' not in json.dumps(transported)
