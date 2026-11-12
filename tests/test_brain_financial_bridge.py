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


def test_extreme_valid_inputs_keep_a_bounded_json_result_and_signed_values():
    for revenue in ('0.000000000001','1','1000000000000000000'):
        for margin in ('-1000','0','0.000000000001','100'):
            for eps in ('0.000000000001','1000000000000000000'):
                p=scenario()
                for period in ('prior','current'):
                    p[period].update(revenue=revenue,gross_margin_pct=margin,
                                     eps=eps,earnings_multiple='1000000000000000000')
                r=analyze(p)
                assert r['status'] in ('partial','complete')
                assert len(json.dumps(r,allow_nan=False)) < 20000
                for cell in r['calculations'].values():
                    if cell['value'] is not None:
                        assert Decimal(cell['value']).is_finite()


def test_missing_values_and_zero_are_distinct_in_the_actual_cli():
    p=scenario(); del p['current']['cash_taxes']
    result=cli(json.dumps(p))
    assert result.returncode==0
    r=json.loads(result.stdout)
    assert value(r,'current.simplified_operating_cash') is None
    assert r['calculations']['current.simplified_operating_cash']['missing_inputs']==['current.cash_taxes']


def test_tool_metadata_defines_cash_signs_and_prevents_double_counting():
    module=importlib.import_module(MODULE)
    tool=module.financial_bridge_tool_schema()
    fields=tool['input_schema']['properties']['current']['properties']
    assert 'excluding cost of sales' in fields['operating_expenses']['description']
    assert 'already deducted' in fields['depreciation_amortization']['description']
    assert 'positive use' in fields['working_capital_increase']['description']
    assert 'not the working-capital balance' in fields['working_capital_increase']['description']
    assert 'not verified facts' in tool['description']


def test_scenario_tests_quantify_reversal_instead_of_only_describing_a_decline():
    p=scenario(); p['prior'].update(eps=5,earnings_multiple=20)
    p['current'].update(eps=6,earnings_multiple=15)
    r=analyze(p)
    assert 'scenario_tests' in r, 'No inspectable reversal tests are available'
    tests=r['scenario_tests']
    expected={'hold.operating_profit_margin_pct':'27.2727272727',
              'hold.operating_profit_revenue':'120',
              'zero.operating_cash_working_capital':'7.5',
              'zero.cash_after_capex_working_capital':'2.5',
              'hold.implied_price_multiple':'16.6666666667',
              'sensitivity.operating_profit_per_margin_pp':'1.1',
              'sensitivity.operating_profit_per_revenue_pct':'0.275',
              'sensitivity.implied_price_per_multiple_turn':'6'}
    for key,expected_value in expected.items():
        assert Decimal(tests[key]['value'])==Decimal(expected_value),key
        assert tests[key]['fixed_inputs'] and tests[key]['formula']
        assert tests[key]['authority']=='conditional_test_only'
    assert tests['hold.operating_profit_margin_pct']['varied_input']=='current.gross_margin_pct'
    assert tests['hold.operating_profit_margin_pct']['target_ref']=='prior.operating_profit'
    assert tests['hold.implied_price_multiple']['unit']=='multiple'


def test_reversal_test_is_replayed_through_the_actual_calculation_owner():
    p=scenario(); r=analyze(p)
    assert 'scenario_tests' in r
    tests=r['scenario_tests']
    cases=[('hold.operating_profit_revenue','revenue','current.operating_profit','10'),
           ('zero.operating_cash_working_capital','working_capital_increase','current.simplified_operating_cash','0'),
           ('zero.cash_after_capex_working_capital','working_capital_increase','current.cash_after_capex','0')]
    for case,field,result_key,expected in cases:
        q=deepcopy(p); q['current'][field]=tests[case]['value']
        assert value(analyze(q),result_key)==Decimal(expected)
    q=deepcopy(p);q['current']['working_capital_increase']='3'
    assert value(analyze(q),'current.cash_after_capex')<0
    q['current']['working_capital_increase']='2'
    assert value(analyze(q),'current.cash_after_capex')>0


def test_untested_rivals_never_become_issuer_facts_or_a_house_signal():
    p=scenario();p['prior'].update(eps=5,earnings_multiple=20);p['current'].update(eps=6,earnings_multiple=15)
    r=analyze(p)
    assert 'reasoning' in r, 'Calculator has no evidence-bound interpretation'
    reasoning=r['reasoning']
    assert reasoning['basis']=='conditional_arithmetic_not_causal_proof'
    assert len(reasoning['findings'])==3
    for finding in reasoning['findings']:
        assert finding['supports'] and finding['reversal_tests']
        assert all(ref in r['calculations'] for ref in finding['supports'])
        assert all(ref in r['scenario_tests'] for ref in finding['reversal_tests'])
        assert len(finding['rivals'])==2
        assert finding['conclusion_type']=='supplied_scenario_implication'
        for rival in finding['rivals']:
            assert rival['status']=='untested'
            assert rival['evidence_to_check'] and rival['would_weaken']
            assert not any(key in rival for key in ('probability','score','confidence','rank'))
    assert reasoning['evidence_retrieval_performed'] is False


def test_no_supported_pattern_means_no_fabricated_narrative():
    p={'basis':'supplied_scenario','currency':'USD','amount_scale':'units',
       'prior':{'period_months':12},'current':{'period_months':12}}
    r=analyze(p)
    assert 'reasoning' in r
    assert r['reasoning']['findings']==[]
    assert all(c['value'] is None for c in r['scenario_tests'].values())
    invalid=analyze({'portfolio':'PRIVATE'});assert invalid['status']=='invalid_request'
    assert not invalid.get('reasoning') and not invalid.get('scenario_tests')


def test_missing_adjustment_blocks_cash_threshold_without_imputing_zero():
    p=scenario();del p['current']['cash_taxes']
    r=analyze(p);assert 'scenario_tests' in r
    for key in ('zero.operating_cash_working_capital','zero.cash_after_capex_working_capital'):
        assert r['scenario_tests'][key]['value'] is None
        assert r['scenario_tests'][key]['missing_inputs']==['current.cash_taxes']
    assert r['scenario_tests']['hold.operating_profit_revenue']['value']=='120'


def test_unrealistic_equality_threshold_is_not_reported_as_a_feasible_fix():
    p=scenario();p['prior'].update(revenue=1000,gross_margin_pct=100,operating_expenses=0)
    r=analyze(p);assert 'scenario_tests' in r
    cell=r['scenario_tests']['hold.operating_profit_margin_pct']
    assert Decimal(cell['value'])>100
    assert cell['within_value_range'] is False
    assert cell['interpretation']=='equality_boundary_not_forecast'


@pytest.mark.parametrize('margin',[0,-10])
def test_nonpositive_margin_does_not_create_a_revenue_repair_claim(margin):
    p=scenario();p['current']['gross_margin_pct']=margin
    r=analyze(p);assert 'scenario_tests' in r
    cell=r['scenario_tests']['hold.operating_profit_revenue']
    assert cell['value'] is None and cell['reason']=='positive_current_margin_required'


def test_annual_price_threshold_can_be_calculated_without_a_current_multiple():
    p=scenario();p['prior'].update(eps=5,earnings_multiple=20);p['current']['eps']=6
    r=analyze(p);assert 'scenario_tests' in r
    assert value(r,'current.implied_price') is None
    assert r['scenario_tests']['hold.implied_price_multiple']['value']=='16.6666666667'
    assert r['scenario_tests']['hold.implied_price_multiple']['missing_inputs']==[]
    p['prior']['period_months']=3;p['current']['period_months']=3
    r=analyze(p)
    assert r['scenario_tests']['hold.implied_price_multiple']['value'] is None
    assert r['scenario_tests']['sensitivity.implied_price_per_multiple_turn']['value'] is None


def test_negative_margin_pattern_does_not_falsely_claim_margin_contracted():
    p=scenario();p['prior']['gross_margin_pct']=-10;p['current']['gross_margin_pct']=-10
    r=analyze(p);assert 'reasoning' in r
    finding=next(f for f in r['reasoning']['findings'] if f['id']=='revenue_up_gross_profit_down')
    assert 'margin contraction' not in finding['conclusion'].lower()
    assert 'does not imply' in finding['conclusion']


def test_reasoning_support_never_cites_an_unavailable_value_as_evidence():
    p=scenario();del p['current']['capital_expenditures']
    r=analyze(p)
    assert value(r,'current.simplified_operating_cash')<0
    assert value(r,'current.cash_after_capex') is None
    for finding in r['reasoning']['findings']:
        assert all(r['calculations'][key]['value'] is not None for key in finding['supports'])


def test_actual_cli_explanation_shows_tests_rivals_and_no_retrieval_claim():
    p=scenario();p['prior'].update(eps=5,earnings_multiple=20);p['current'].update(eps=6,earnings_multiple=15)
    run=subprocess.run([sys.executable,'-m','scripts.analyze_financial_bridge','--explain'],
                       cwd=ROOT,input=json.dumps(p),text=True,capture_output=True,timeout=15)
    assert run.returncode==0,run.stdout
    assert run.stderr==''
    for phrase in ('Conditional financial analysis','27.2727272727','120','16.6666666667',
                   'Untested rival','Evidence to check','Would weaken','No company evidence was retrieved',
                   'caller-supplied, unverified','current.cash_after_capex: -5.5'):
        assert phrase in run.stdout,phrase
    assert len(run.stdout)<16000


def test_explanation_does_not_hide_missing_inputs_or_emit_rejected_private_text():
    p=scenario();del p['current']['cash_taxes']
    run=subprocess.run([sys.executable,'-m','scripts.analyze_financial_bridge','--explain'],
                       cwd=ROOT,input=json.dumps(p),text=True,capture_output=True,timeout=15)
    assert run.returncode==0
    assert 'current.cash_taxes' in run.stdout and 'unavailable' in run.stdout
    p['portfolio']='PRIVATE_CUSTOMER_CONTENT'
    run=subprocess.run([sys.executable,'-m','scripts.analyze_financial_bridge','--explain'],
                       cwd=ROOT,input=json.dumps(p),text=True,capture_output=True,timeout=15)
    assert run.returncode==2
    assert json.loads(run.stdout)['status']=='invalid_request'
    assert 'PRIVATE_CUSTOMER_CONTENT' not in run.stdout


def test_sensitivity_distinguishes_a_reference_base_from_an_input_held_fixed():
    r=analyze(scenario())
    cell=r['scenario_tests']['sensitivity.operating_profit_per_revenue_pct']
    assert cell['varied_input']=='current.revenue'
    assert 'current.revenue' not in cell['fixed_inputs']
    assert cell['baseline_inputs']==['current.revenue']
    assert cell['fixed_inputs']==['current.gross_margin_pct']


def test_random_equality_thresholds_reproduce_their_named_targets():
    import random
    rng=random.Random(260917)
    for _ in range(150):
        p=scenario()
        p['prior'].update(revenue=rng.randint(50,200),gross_margin_pct=rng.randint(20,70),operating_expenses=5)
        p['current'].update(revenue=rng.randint(50,200),gross_margin_pct=rng.randint(20,70),operating_expenses=5)
        r=analyze(p)
        for key,field in (('hold.operating_profit_margin_pct','gross_margin_pct'),
                          ('hold.operating_profit_revenue','revenue')):
            cell=r['scenario_tests'][key]
            if cell['within_value_range']:
                q=deepcopy(p);q['current'][field]=cell['value']
                rr=analyze(q)
                assert abs(value(rr,'current.operating_profit')-value(r,'prior.operating_profit'))<Decimal('0.00000001')
        q=deepcopy(p);q['current']['working_capital_increase']=r['scenario_tests']['zero.cash_after_capex_working_capital']['value']
        assert abs(value(analyze(q),'current.cash_after_capex'))<Decimal('0.00000001')


# Actual Brain registration/dispatch integration (provider responses remain fixtures).
def test_real_brain_registry_offers_exactly_one_calculator_in_chat(tmp_path,monkeypatch):
    from engine.neuralweb import brain_gateway as gw
    import inspect
    assert 'calculate_financial_bridge' in gw._BRAIN_TOOLS
    assert 'calculate_financial_bridge' in gw._BRAIN_ONLY_TOOLS
    assert gw._BRAIN_INTERNALS_TOOLS==frozenset({'context_search','context_open'})
    assert 'mode' in inspect.signature(gw._all_brain_tool_schemas).parameters
    monkeypatch.setattr(gw,'_resolve_tier',lambda *a,**k:{'tier':'free','status':'none'})
    offered=gw._all_brain_tool_schemas(tmp_path,mode='chat')
    selected=[t for t in offered if t['name']=='calculate_financial_bridge']
    assert selected==[importlib.import_module(MODULE).financial_bridge_tool_schema()]
    assert not any(t['name'] in gw._BRAIN_INTERNALS_TOOLS for t in offered)


def test_actual_brain_dispatch_calls_the_existing_calculator_without_extra_io(tmp_path,monkeypatch):
    from engine.neuralweb import brain_gateway as gw
    import socket
    module=importlib.import_module(MODULE)
    expected=module.analyze_financial_bridge(scenario())
    calls=[]; original=module.analyze_financial_bridge
    def invoke(p):
        calls.append(deepcopy(p));return original(p)
    def forbidden(*a,**k):raise AssertionError('unexpected data, network or entitlement access')
    monkeypatch.setattr(module,'analyze_financial_bridge',invoke)
    monkeypatch.setattr(socket,'socket',forbidden)
    monkeypatch.setattr(gw,'_resolve_tier',forbidden)
    result=gw._dispatch_brain_tool('calculate_financial_bridge',scenario(),tmp_path,tmp_path,'http://unused')
    assert result==expected
    assert calls==[scenario()]


@pytest.mark.parametrize('mode',['research',' Research ','unknown',None])
def test_calculator_is_not_offered_or_executed_outside_chat(tmp_path,monkeypatch,mode):
    from engine.neuralweb import brain_gateway as gw
    import inspect
    assert 'mode' in inspect.signature(gw._all_brain_tool_schemas).parameters
    assert 'mode' in inspect.signature(gw._dispatch_brain_tool).parameters
    module=importlib.import_module(MODULE)
    def forbidden(*a,**k):raise AssertionError('non-chat calculation ran')
    monkeypatch.setattr(module,'analyze_financial_bridge',forbidden)
    monkeypatch.setattr(gw,'_resolve_tier',lambda *a,**k:{'tier':'free','status':'none'})
    assert not any(s['name']=='calculate_financial_bridge' for s in gw._all_brain_tool_schemas(tmp_path,mode=mode))
    r=gw._dispatch_brain_tool('calculate_financial_bridge',scenario(),tmp_path,tmp_path,'http://unused',mode=mode)
    assert r.get('error')
    assert not r.get('calculations')


def test_dispatch_rejects_forged_privileged_fields_without_echo(tmp_path):
    from engine.neuralweb import brain_gateway as gw
    p=scenario();p['user_id']='PRIVATE_ACCOUNT';p['provider']='PRIVATE_PROVIDER'
    r=gw._dispatch_brain_tool('calculate_financial_bridge',p,tmp_path,tmp_path,'http://unused')
    assert r.get('status')=='invalid_request'
    assert not r.get('calculations')
    assert 'PRIVATE_' not in json.dumps(r)


class _BridgeResponseClient:
    """Scripted provider boundary; real registry, dispatcher and loops below."""
    def __init__(self,payload):
        self.payload=payload;self.messages=self;self.calls=[];self.tool_result=None
    def create(self,**kwargs):
        from tests.test_brain_gateway import _MockBlock,_MockResponse
        self.calls.append(deepcopy(kwargs))
        if len(self.calls)==1:
            names=[s['name'] for s in kwargs.get('tools',[])]
            assert names.count('calculate_financial_bridge')==1
            return _MockResponse([_MockBlock('tool_use',name='calculate_financial_bridge',
                                             input_=self.payload,id_='bridge-test')],'tool_use')
        found=[]
        for message in kwargs.get('messages',[]):
            content=message.get('content')
            if isinstance(content,list):
                found.extend(block for block in content if isinstance(block,dict)
                             and block.get('type')=='tool_result' and block.get('tool_use_id')=='bridge-test')
        assert len(found)==1,'Real tool result did not reach the next provider round'
        self.tool_result=json.loads(found[0]['content'])
        assert self.tool_result['input_provenance']=='caller_supplied_unverified'
        cells=self.tool_result['calculations']
        op=cells['current.operating_profit']['value']
        cash=cells['current.simplified_operating_cash']['value']
        answer=f'Using the supplied assumptions, operating profit is {op}; operating cash is {cash if cash is not None else "unavailable"}. Prior operating cash is unknown. These calculations do not establish a cause or a price target.'
        return _MockResponse([_MockBlock('text',answer)],'end_turn')
    def stream(self,**kwargs):
        from tests.test_brain_gateway import _ScriptedStreamCtx
        return _ScriptedStreamCtx(self.create(**kwargs))


@pytest.mark.parametrize('stream',[False,True])
@pytest.mark.parametrize('missing_tax',[False,True])
def test_real_chat_loops_deliver_calculation_to_next_round_and_final_output(tmp_path,monkeypatch,stream,missing_tax):
    from engine.neuralweb import brain_gateway as gw
    from tests.test_brain_gateway import _make_temp_root,_sse
    import socket
    payload=scenario()
    if missing_tax:del payload['current']['cash_taxes']
    client=_BridgeResponseClient(payload)
    module=importlib.import_module(MODULE);original=module.analyze_financial_bridge;calls=[]
    def calculate(p):calls.append(deepcopy(p));return original(p)
    def no_network(*a,**k):raise AssertionError('offline integration used network')
    monkeypatch.setattr(module,'analyze_financial_bridge',calculate)
    monkeypatch.setattr(socket,'socket',no_network)
    monkeypatch.setattr(gw,'_brain_quota_dir',lambda *a,**k:tmp_path/'quota')
    monkeypatch.setattr(gw,'_build_lane_providers',lambda *a,**k:[{'name':'deepseek','model':'deepseek-chat','client':client}])
    monkeypatch.setattr(gw,'_resolve_tier',lambda *a,**k:{'tier':'pro','status':'active','current_period_end':None})
    monkeypatch.setattr(gw,'_ensure_thread',lambda *a,**k:None)
    monkeypatch.setattr(gw,'_instant_route',lambda *a,**k:None)
    monkeypatch.setattr('lib.ai_costs.record_usage',lambda **k:True)
    monkeypatch.setattr('lib.ai_costs._write_ledger_path',lambda root=None:tmp_path/'costs.jsonl')
    root=_make_temp_root()
    question='Analyze this supplied financial scenario and explain profit versus cash.'
    if stream:
        events=_sse(list(gw.chat_stream(question,'u-fixture-bridge',lane='fast',root=root,mode='chat')))
        assert events[0]['type']=='meta' and events[-1]['type']=='done'
        rendered=''.join(e.get('text','') for e in events if e['type']=='delta')
    else:
        result=gw.chat(question,'u-fixture-bridge',lane='fast',root=root,mode='chat')
        assert result.get('ok') is True,result
        rendered=result.get('reply') or result.get('answer') or result.get('text') or ''
    assert calls==[payload]
    assert client.tool_result['calculations']['current.operating_profit']['value']=='7.5'
    assert client.tool_result['calculations']['current.simplified_operating_cash']['value']==(None if missing_tax else '-0.5')
    assert 'operating profit is 7.5' in rendered,rendered
    assert ('operating cash is unavailable' if missing_tax else 'operating cash is -0.5') in rendered
    assert 'supplied assumptions' in rendered


class _ResearchCalculationAttemptClient(_BridgeResponseClient):
    def create(self,**kwargs):
        from tests.test_brain_gateway import _MockBlock,_MockResponse
        self.calls.append(deepcopy(kwargs))
        if len(self.calls)==1:
            assert 'calculate_financial_bridge' not in [s['name'] for s in kwargs.get('tools',[])]
            return _MockResponse([_MockBlock('tool_use',name='calculate_financial_bridge',
                                             input_=self.payload,id_='bridge-denied')],'tool_use')
        for message in kwargs.get('messages',[]):
            if isinstance(message.get('content'),list):
                for block in message['content']:
                    if isinstance(block,dict) and block.get('type')=='tool_result' and block.get('tool_use_id')=='bridge-denied':
                        self.tool_result=json.loads(block['content'])
        assert self.tool_result and self.tool_result.get('error')
        assert not self.tool_result.get('calculations')
        return _MockResponse([_MockBlock('text','This mode did not run the requested calculation.')],'end_turn')


@pytest.mark.parametrize('stream',[False,True])
def test_real_research_loops_refuse_unoffered_calculator_even_when_provider_requests_it(tmp_path,monkeypatch,stream):
    from engine.neuralweb import brain_gateway as gw
    from tests.test_brain_gateway import _make_temp_root,_sse
    import socket
    client=_ResearchCalculationAttemptClient(scenario())
    def forbidden(*a,**k):raise AssertionError('research attempted calculation or network')
    monkeypatch.setattr(importlib.import_module(MODULE),'analyze_financial_bridge',forbidden)
    monkeypatch.setattr(socket,'socket',forbidden)
    monkeypatch.setattr(gw,'_brain_quota_dir',lambda *a,**k:tmp_path/'quota')
    monkeypatch.setattr(gw,'_build_lane_providers',lambda *a,**k:[{'name':'deepseek','model':'deepseek-chat','client':client}])
    monkeypatch.setattr(gw,'_resolve_tier',lambda *a,**k:{'tier':'pro','status':'active','current_period_end':None})
    monkeypatch.setattr(gw,'_ensure_thread',lambda *a,**k:None)
    monkeypatch.setattr(gw,'_instant_route',lambda *a,**k:None)
    monkeypatch.setattr('lib.ai_costs.record_usage',lambda **k:True)
    monkeypatch.setattr('lib.ai_costs._write_ledger_path',lambda root=None:tmp_path/'costs.jsonl')
    root=_make_temp_root()
    if stream:
        events=_sse(list(gw.chat_stream('Read published research.','u-bridge-research',lane='pro',mode='research',root=root)))
        assert events[-1]['type']=='done'
    else:
        result=gw.chat('Read published research.','u-bridge-research',lane='pro',mode='research',root=root)
        assert result.get('ok') is True,result
    assert client.tool_result and client.tool_result.get('error')
    assert not client.tool_result.get('calculations')


def test_financial_bridge_suite_is_owned_by_existing_premerge_gateway_job():
    import shlex
    import yaml
    jobs=yaml.safe_load((ROOT/'.github/ci/legacy-jobs.yml').read_text())['jobs']
    owners=[]
    for name,job in jobs.items():
        for step in job.get('steps',[]):
            if 'tests/test_brain_financial_bridge.py' in shlex.split(step.get('run','')):
                owners.append(name)
                assert job.get('gate')=='code'
                assert not step.get('continue-on-error')
                assert not step.get('if')
    assert owners==['unrun-brain-gateway']


def test_existing_progress_event_has_bilingual_safe_calculation_labels():
    from engine.neuralweb import brain_gateway as gw
    raw=gw._tool_event('calculate_financial_bridge',scenario())
    event=json.loads(raw[6:])
    assert event['name']=='calculate_financial_bridge'
    assert event['label_en']=='Checking the financial assumptions'
    assert event['label_zh']=='核算财务假设'
    assert 'detail' not in event
    assert 'gross_margin_pct' not in raw and 'operating_expenses' not in raw


def test_nonchat_unknown_tool_disclosure_does_not_advertise_calculator(tmp_path,monkeypatch):
    from engine.neuralweb import brain_gateway as gw
    monkeypatch.setattr(gw,'_resolve_tier',lambda *a,**k:{'tier':'free','status':'none'})
    result=gw._dispatch_brain_tool('nonexistent',{},tmp_path,tmp_path,'http://unused',mode='research')
    assert 'calculate_financial_bridge' not in result.get('available_tools',[])
