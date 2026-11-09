from copy import deepcopy
import json
from pathlib import Path
import pytest
from engine.government_revenue.defense_interpretation import build_defense_interpretation,validate_defense_interpretation
from engine.government_revenue.defense_economics import validate_defense_economics_payload,defense_economics_content_id

FIXTURE=Path(__file__).parent/'fixtures'/'defense_interpretation.json'

def snapshot():return json.loads(FIXTURE.read_text())
def profile(payload,ticker):return next(p for p in payload['profiles'] if p['ticker_display']==ticker)

def test_all_four_source_bound_chains_and_conditional_cases_leave_axes_and_valuation_truthful():
    payload=snapshot();assert validate_defense_economics_payload(payload)
    for p in payload['profiles']:
        interp=p['interpretation'];assert [c['stage'] for c in interp['chain']]==['demand','capture','margin','common_cash']
        assert interp['chain'][0]['state']=='unknown'
        assert [c['kind'] for c in interp['scenarios']]==['conditional_baseline','downside']
        assert p['axes']['participation']['state']=='missing_owner' and p['axes']['demand']['state']=='missing_owner'
        assert p['research_state']=='EVIDENCE_INSUFFICIENT' and p['program_workshare'] is None
        assert p['axes']['recognition'].get('valuation_scenario',{'state':'missing_owner'})['state']=='missing_owner'
        facts={(f['fact_id'],f['owner_ref']):f for f in p['axes']['economics']['facts']}
        for row in [*interp['chain'],*interp['scenarios']]:
            assert row['owner_refs']==[] and row['fact_refs']
            assert all((r['fact_id'],r['owner_ref']) in facts for r in row['fact_refs'])
        assert all(row['summary_zh'] for row in interp['chain']) and all(row['assumption_zh'] and row['invalidation_zh'] for row in interp['scenarios'])


def test_noc_current_adverse_and_prior_favorable_do_not_net_or_assume_margin_reversion():
    p=profile(snapshot(),'NOC');text=json.dumps(p['interpretation'],ensure_ascii=False)
    assert '68' in text and '76' in text and '7.5' in text and '12.7' in text
    assert 'different program' in text and 'cannot be netted' in text and 'does not establish margin reversion' in text
    assert not any(k in p['interpretation'] for k in ('normalized_profit','normalized_margin','forecast','per_share'))


def test_lhx_sale_basis_scope_and_company_forward_conversion_remain_distinct():
    p=profile(snapshot(),'LHX');text=json.dumps(p['interpretation'],ensure_ascii=False)
    assert '845' in text and '40%' in text and 'RS-25' in text and 'pending net-value basis' in text
    assert '20% discount' in text and '10% QIPO stake is a company expectation' in text
    assert 'do not equal common-holder cash' in text and 'No current dilution percentage' in text


@pytest.mark.parametrize('fault',['private_body','forecast_text','wrong_fact','foreign_owner','supported_demand','numerical_field','changed_unknown','unlinked_text'])
def test_rehashed_interpretation_cannot_invent_claims_or_provenance(fault):
    payload=snapshot();p=profile(payload,'LMT');interp=p['interpretation']
    if fault=='private_body':interp['private_body']='PRIVATE'
    if fault=='forecast_text':interp['scenarios'][0]['implication_en']='Guaranteed 50% revenue growth.'
    if fault=='wrong_fact':interp['chain'][2]['fact_refs'][0]['fact_id']='unknown_fact'
    if fault=='foreign_owner':interp['chain'][2]['fact_refs'][0]=deepcopy(profile(payload,'NOC')['interpretation']['chain'][2]['fact_refs'][0])
    if fault=='supported_demand':interp['chain'][0]['state']='reported'
    if fault=='numerical_field':interp['scenarios'][0]['per_share']=123
    if fault=='changed_unknown':interp['unknowns'].remove('program_workshare')
    if fault=='unlinked_text':interp['chain'][2]['fact_refs']=[]
    payload['content_id']=defense_economics_content_id(payload)
    with pytest.raises(ValueError,match='interpretation'):validate_defense_economics_payload(payload)


def test_missing_core_baseline_and_changed_lhx_terms_do_not_reuse_unsupported_narrative():
    payload=snapshot();p=profile(payload,'LMT');facts=deepcopy(p['axes']['economics']['facts']);facts.pop()
    assert build_defense_interpretation('LMT',facts) is None
    p=profile(payload,'LHX');facts=deepcopy(p['axes']['economics']['facts'])
    next(f for f in facts if f['fact_id'].endswith(':space_business_sale_completed_terms'))['value']='completed sale at $885 million'
    changed=build_defense_interpretation('LHX',facts)
    assert '845' not in json.dumps(changed) and changed['chain'][1]['state']=='unknown'


def test_old_closed_snapshots_without_optional_interpretation_remain_valid():
    payload=snapshot()
    for p in payload['profiles']:p.pop('interpretation')
    payload['content_id']=defense_economics_content_id(payload)
    assert validate_defense_economics_payload(payload)
