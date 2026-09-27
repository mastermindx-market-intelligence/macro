"""Tests of the proposed F07 contract; all amounts and identities are synthetic."""
import copy
from decimal import Decimal as D
import pytest
from f07_scenario_reference import ContractError, evaluate


def packet(method='common_earnings_multiple'):
    state = {
        'id':'up', 'probability':'0.6', 'valuation_at':'2027-03-27',
        'earnings_period':{'start':'2027-03-28','end':'2028-03-27','basis':'forward_12m'},
        'revenue':'1000','gross_margin':'0.5','operating_expense':'200',
        'interest_expense':'20','income_tax_expense':'56','other_income_claims':'4',
        'method':method,'multiple':'10' if method=='common_earnings_multiple' else None,
        'operating_enterprise_value':'1800' if method=='operating_enterprise' else None,
        'other_senior_claims':'0', 'dividend_to_entry_share':'0.2',
        'cash_flow':{'operating_after_interest_tax':'100','capex':'60',
                     'new_common_shares':'10','equity_issue_price':'10',
                     'equity_issue_fees':'5','new_debt':'20','debt_repayment':'10',
                     'distributions_paid':'25'},
    }
    down=copy.deepcopy(state);down['id']='down';down['probability']='0.4'
    down['gross_margin']='0.3';down['income_tax_expense']='10';down['other_income_claims']='0'
    if method=='operating_enterprise':down['operating_enterprise_value']='600'
    return {'mode':'synthetic_reference','version':'fixture-v1','subject_ref':'fixture-security',
            'financial_ref':'fixture-finance','rights_ref':'fixture-common-claim',
            'forecast_ref':'fixture-joint-forecast','known_at':'2026-09-26T12:00:00Z',
            'as_of':'2026-09-27T12:00:00Z','horizon':'2027-03-27',
            'currency':'USD','money_unit':'currency_units',
            'quote':{'id':'fixture-quote','observed_at':'2026-09-27T11:59:00Z',
                     'valid_until':'2026-09-27T12:01:00Z','price':'10','currency':'USD'},
            'opening_cash':'100','opening_debt':'50','opening_common_shares':'100',
            'roundtrip_cost_fraction':'0.01','probability_semantics':'illustrative_partition',
            'states':[state,down]}


def run(p=None):return evaluate(p or packet(),expected_version='fixture-v1')
def num(v):return D(v)

def test_gross_to_common_not_gross_to_pe():
    r=run()['states'][0]
    assert num(r['gross_profit'])==500
    assert num(r['operating_income'])==300
    assert num(r['net_common_income'])==220
    assert num(r['equity_value'])==2200

def test_pe_does_not_add_cash_or_subtract_debt_twice():
    p=packet();r=run(p);p['opening_cash']='800';p['opening_debt']='700'
    assert run(p)['states'][0]['equity_value']==r['states'][0]['equity_value']

def test_cash_debt_issuance_reconcile():
    s=run()['states'][0]
    assert num(s['horizon_cash'])==220
    assert num(s['horizon_debt'])==60
    assert num(s['horizon_common_shares'])==110
    assert num(s['price_at_horizon'])==20

def test_enterprise_to_common_equity_bridge():
    r=run(packet('operating_enterprise'))['states'][0]
    assert num(r['equity_value'])==1960
    assert num(r['equity_residual_before_floor'])==1960

def test_senior_claims_apply_only_to_enterprise_bridge():
    p=packet('operating_enterprise');p['states'][0]['other_senior_claims']='100'
    assert num(run(p)['states'][0]['equity_value'])==1860

def test_negative_enterprise_residual_is_visible_not_hidden():
    p=packet('operating_enterprise');p['states'][0]['other_senior_claims']='2500'
    s=run(p)['states'][0]
    assert num(s['equity_residual_before_floor'])==-540
    assert num(s['equity_value'])==0 and s['limited_liability_floor_applied'] is True

def test_dividend_is_per_original_share_not_terminal_average():
    r=run()['states'][0]
    assert num(r['net_return'])==D('1.01')
    assert num(r['gross_return'])==D('1.02')

def test_joint_weighting_preserves_state_dependence():
    p=packet();a=run(p)
    expected=sum(D(s['probability'])*num(o['net_return']) for s,o in zip(p['states'],a['states']))
    assert abs(num(a['illustrative_expected_net_return'])-expected)<D('1e-24')
    assert a['probability_of_positive_net_return']=='0.6'

def test_conditional_values_remain_when_probabilities_absent():
    p=packet();p['probability_semantics']='unweighted_conditional'
    for s in p['states']:s['probability']=None
    r=run(p)
    assert r['status']=='conditional_only'
    assert r['illustrative_expected_net_return'] is None
    assert r['probability_of_positive_net_return'] is None
    assert num(r['states'][0]['price_at_horizon'])==20

def test_no_authority_or_live_forecast_from_reference():
    r=run()
    assert r['can_rank'] is False and r['production_admission'] is False
    assert r['recommendation'] is None and r['calibrated_probability'] is None
    assert r['scope']=='synthetic_contract_reference'

def test_input_is_not_mutated_and_export_is_json_ready():
    import json
    p=packet();old=copy.deepcopy(p);r=run(p)
    assert p==old;assert json.loads(json.dumps(r))==r

def test_hypothetical_price_changes_return_not_equity_or_odds():
    p=packet();a=run(p);p['quote']['price']='20';b=run(p)
    for x,y in zip(a['states'],b['states']):
        assert x['equity_value']==y['equity_value'] and x['probability']==y['probability']
    assert a['illustrative_expected_net_return']!=b['illustrative_expected_net_return']

def test_dependent_issue_price_revalues_cash_and_enterprise_equity():
    p=packet('operating_enterprise');a=run(p);p['states'][0]['cash_flow']['equity_issue_price']='20';b=run(p)
    assert num(b['states'][0]['horizon_cash'])-num(a['states'][0]['horizon_cash'])==100
    assert num(b['states'][0]['equity_value'])-num(a['states'][0]['equity_value'])==100

def test_company_cash_not_assumed_shareholder_distribution():
    p=packet();p['opening_cash']='5000';r=run(p)
    assert r['states'][0]['dividend_to_entry_share']=='0.2'
    assert num(r['states'][0]['gross_return'])==D('1.02')

def test_exact_version_and_binding_are_retained():
    p=packet();r=run(p)
    for k in ('version','subject_ref','financial_ref','rights_ref','forecast_ref','as_of','horizon','currency'):
        assert r['binding'][k]==p[k]
    assert r['binding']['quote_id']==p['quote']['id']

@pytest.mark.parametrize('path,value,code',[
    (('mode',),'production','reference_only'),
    (('version',),'moved','version_mismatch'),
    (('rights_ref',),None,'missing_binding'),
    (('financial_ref',),'','missing_binding'),
    (('forecast_ref',),'','missing_binding'),
    (('known_at',),'2026-09-28T00:00:00Z','future_input'),
    (('known_at',),'2026-09-26T00:00:00','timezone_required'),
    (('horizon',),'2026-09-27','horizon_not_future'),
    (('money_unit',),'USD_m','unit_mismatch'),
    (('quote','currency'),'CAD','currency_mismatch'),
    (('quote','observed_at'),'2026-09-28T00:00:00Z','future_quote'),
    (('quote','valid_until'),'2026-09-27T12:00:00Z','stale_quote'),
    (('quote','price'),'0','positive_required'),
    (('quote','price'),True,'numeric_type'),
    (('quote','price'),'NaN','nonfinite'),
    (('quote','price'),'Infinity','nonfinite'),
    (('opening_common_shares',),'0','positive_required'),
    (('states',0,'valuation_at'),'2027-04-27','horizon_mismatch'),
    (('states',0,'earnings_period','end'),'2027-06-27','annual_basis_required'),
    (('states',0,'gross_margin'),'1.1','margin_above_one'),
    (('states',0,'revenue'),'-1','nonnegative_required'),
    (('states',0,'cash_flow','capex'),'1000','unfunded_path'),
    (('states',0,'cash_flow','debt_repayment'),'1000','negative_debt'),
    (('states',0,'cash_flow','equity_issue_price'),None,'missing_numeric'),
    (('states',0,'dividend_to_entry_share'),'1','distribution_inconsistent'),
    (('states',0,'other_senior_claims'),'1','pe_claim_basis'),
    (('states',0,'operating_enterprise_value'),'2000','mixed_valuation_methods'),
    (('states',0,'probability'),'0.7','weights_not_one'),
    (('states',0,'probability'),None,'partial_probabilities'),
    (('states',1,'id'),'up','duplicate_state'),
    (('probability_semantics',),'calibrated','unsupported_probability_semantics'),
])
def test_invalid_contract(path,value,code):
    p=packet();d=p
    for k in path[:-1]:d=d[k]
    d[path[-1]]=value
    with pytest.raises(ContractError,match=code):run(p)


def test_quarter_cannot_be_relabelled_as_annual():
    p=packet();p['states'][0]['earnings_period']['basis']='quarterly'
    with pytest.raises(ContractError,match='annual_basis_required'):run(p)

def test_missing_forecast_cost_does_not_become_zero():
    p=packet();p['states'][0]['operating_expense']=None
    with pytest.raises(ContractError,match='missing_numeric'):run(p)

def test_common_earnings_nonpositive_requires_different_model():
    p=packet();p['states'][0]['gross_margin']='0.1'
    with pytest.raises(ContractError,match='nonpositive_pe_earnings'):run(p)

def test_nonexhaustive_weights_not_silently_renormalized():
    p=packet();p['states']=p['states'][:1]
    with pytest.raises(ContractError,match='weights_not_one'):run(p)

def test_wrong_shared_base_does_not_blend_states():
    p=packet();p['states'][0]['currency']='CAD'
    with pytest.raises(ContractError,match='unknown_fields'):run(p)

def test_no_raise_has_no_issue_price_or_fee():
    p=packet()
    for s in p['states']:
        s['cash_flow']['new_common_shares']='0';s['cash_flow']['equity_issue_price']=None
        s['cash_flow']['equity_issue_fees']='0'
    assert num(run(p)['states'][0]['horizon_cash'])==125

def test_new_shares_are_terminal_not_weighted_average():
    p=packet();p['states'][0]['weighted_average_diluted_shares']='105'
    with pytest.raises(ContractError,match='unknown_fields'):run(p)


def test_aggregate_cash_is_not_a_liquidity_survival_proof():
    r=run()
    assert r['liquidity_path_assessed'] is False
    assert 'Endpoint cash does not prove interim funding availability.' in r['limitations']

def test_semiconductor_joint_margins_are_not_averaged_before_multiplication():
    p=packet()
    p['states'][0]['revenue']='1200';p['states'][1]['revenue']='800'
    r=run(p)
    true_gp=sum(D(s['probability'])*num(v['gross_profit']) for s,v in zip(p['states'],r['states']))
    product_of_means=(sum(D(s['probability'])*D(s['revenue']) for s in p['states'])
                      *sum(D(s['probability'])*D(s['gross_margin']) for s in p['states']))
    assert true_gp==D('456') and product_of_means==D('436.8')
    assert true_gp != product_of_means

@pytest.mark.parametrize('method',["operating_enterprise","common_earnings_multiple"])
def test_shared_base_refs_cannot_be_overridden_inside_a_branch(method):
    p=packet(method);p['states'][0]['rights_ref']='different-claim'
    with pytest.raises(ContractError,match='unknown_fields'):run(p)


def test_zero_probability_is_valid_not_treated_as_missing():
    p=packet();p['states'][0]['probability']='0';p['states'][1]['probability']='1'
    r=run(p)
    assert r['status']=='illustrative_weighted'
    assert r['illustrative_expected_net_return']==r['states'][1]['net_return']


def test_claimed_calibration_cannot_unlock_ranking():
    p=packet();p['calibration_passed']=True
    with pytest.raises(ContractError,match='unknown_fields'):run(p)

@pytest.mark.parametrize('weights', [(D('0.6'),D('0.4')), (1,0)])
def test_accepted_numeric_probability_types_export_canonically(weights):
    import json
    p=packet()
    for state,weight in zip(p['states'],weights):state['probability']=weight
    r=run(p)
    assert all(isinstance(s['probability'],str) for s in r['states'])
    assert [D(s['probability']) for s in r['states']]==list(map(D,weights))
    assert json.loads(json.dumps(r))==r
