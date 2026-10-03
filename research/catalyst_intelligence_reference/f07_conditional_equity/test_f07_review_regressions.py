"""Regression obligations from independent review 5331568561; synthetic only."""
import copy, hashlib, json
from decimal import Decimal as D
import pytest
from test_f07_scenario_reference import packet, run
from f07_scenario_reference import ContractError, evaluate


def test_pe_cannot_discard_fresh_issue_proceeds():
    p=packet('common_earnings_multiple')
    for s in p['states']:
        s['cash_flow'].update(new_common_shares='10',equity_issue_price='100',equity_issue_fees='5')
    with pytest.raises(ContractError,match='pe_financing_out_of_scope'):run(p)


def test_preinformation_price_cannot_be_used_as_entry():
    p=packet('operating_enterprise')
    p['known_at']='2026-09-27T12:00:00Z'
    p['quote']['observed_at']='2026-09-27T11:00:00Z'
    with pytest.raises(ContractError,match='quote_precedes_information'):run(p)


def test_missing_security_share_basis_is_refused():
    p=packet('operating_enterprise');p.pop('share_basis_ref',None)
    with pytest.raises(ContractError,match='missing_fields'):run(p)


def test_result_contains_replayable_immutable_input():
    p=packet('operating_enterprise');old=copy.deepcopy(p);r=run(p)
    assert 'input_envelope' in r
    body=json.dumps(r['input_envelope'],sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()
    assert r['input_sha256']==hashlib.sha256(body).hexdigest()
    assert evaluate(json.loads(body),expected_version=p['version'])==r
    p['states'][0]['revenue']='9999'
    assert r['input_envelope']['states'][0]['revenue']==old['states'][0]['revenue']


def test_result_preserves_price_cost_clocks_and_model_inputs():
    p=packet('operating_enterprise');r=run(p)
    e=r.get('input_envelope',{})
    for k in ('known_at','quote','opening_cash','opening_debt','opening_common_shares','roundtrip_cost_fraction','states'):
        assert e.get(k)==p[k]

@pytest.mark.parametrize('field,value,reason',[
    ('subject_ref','other-security','quote_subject_mismatch'),
    ('share_basis_ref','different-common-class','quote_share_basis_mismatch'),
    ('common_shares_per_unit','2','share_conversion_not_supported'),
    ('common_shares_per_unit','0.5','share_conversion_not_supported'),
    ('common_shares_per_unit','0','positive_required'),
    ('subject_ref',None,'missing_binding'),
    ('share_basis_ref','', 'missing_binding'),
])
def test_quote_cannot_cross_instruments_or_share_bases(field,value,reason):
    p=packet('operating_enterprise');p['quote'][field]=value
    with pytest.raises(ContractError,match=reason):run(p)


def test_quote_exactly_at_information_time_is_structurally_eligible():
    p=packet('operating_enterprise');p['quote']['observed_at']=p['known_at']
    r=run(p)
    assert r['binding']['known_at']==p['known_at']
    assert r['binding']['share_basis_ref']==p['share_basis_ref']
    assert 'Post-information quote ordering is not an executable-fill receipt.' in r['limitations']


def test_issue_price_sensitivity_uses_the_financing_aware_family():
    a=packet('operating_enterprise');b=copy.deepcopy(a)
    b['states'][0]['cash_flow']['equity_issue_price']='100'
    x,y=run(a)['states'][0],run(b)['states'][0]
    assert D(y['horizon_cash'])-D(x['horizon_cash'])==900
    assert D(y['equity_value'])-D(x['equity_value'])==900
    assert abs(D(y['price_at_horizon'])-D(x['price_at_horizon'])-D(900)/D(110))<D('1e-24')


def test_replay_handles_decimal_and_integer_inputs_without_external_records():
    p=packet('operating_enterprise');p['states'][0]['probability']=D('0.6')
    p['states'][1]['probability']=D('0.4');p['quote']['price']=10
    r=run(p);body=json.dumps(r)
    decoded=json.loads(body)
    assert evaluate(decoded['input_envelope'],expected_version='fixture-v1')==decoded
    assert decoded['input_envelope']['quote']['price']=='10'


def test_same_labels_with_different_assumptions_get_different_digests():
    p=packet('operating_enterprise');a=run(p);p['states'][0]['operating_enterprise_value']='1900';b=run(p)
    assert a['binding']==b['binding']
    assert a['input_sha256']!=b['input_sha256']
