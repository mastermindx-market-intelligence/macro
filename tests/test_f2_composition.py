from pathlib import Path
from copy import deepcopy
from hashlib import sha256
import pytest
from engine.government_revenue.defense_economics_producer import build_defense_economics_payload,load_defense_owner_snapshot
from engine.company_intelligence.contracts import canonical_json_bytes
from datetime import date
import json
from engine.company_intelligence.event_workspace import write_workspace_generation
from engine.company_intelligence.event_workspace_build import build_event_workspace
from engine.company_intelligence.identity import IssuerRegistry
from engine.company_intelligence.noc_adverse_profile import noc_adverse_profile
from engine.company_intelligence.issuer_supplements import append_issuer_supplements
from engine.company_intelligence import defense_profiles as profiles
from tests.test_government_revenue_defense_owner_adapter import make_workspace
from tests.test_issuer_supplements import held
from engine.earnings_release.binding import bind_release_document
FIXTURES=Path(__file__).with_name('fixtures')/'company_intelligence'/'defense'

@pytest.fixture
def BASE(tmp_path):
    rows={}
    for ticker in profiles.DEFENSE_TICKERS:
        row=make_workspace(ticker);rows[row['event_id']]=row
    filing=json.loads((FIXTURES/'NOC.filing.json').read_text());body=(FIXTURES/'NOC.adverse.html').read_text()
    bound=bind_release_document(body=body,**filing)
    row=build_event_workspace(registry=IssuerRegistry(profiles.defense_issuer(t) for t in profiles.DEFENSE_TICKERS),ticker='NOC',asof=date.fromisoformat(filing['filing_date']),fiscal_period=profiles.source_fiscal_period(bound,'NOC'),exhibit_body=body,filing=filing,transcript=None,observed_at='2026-10-13T03:03:46Z',source_available_at=filing['acceptance_datetime'],profile=noc_adverse_profile())
    rows[row['event_id']]=row
    lhx=rows['evt_cik0000202058_2026q2_results']
    rows[lhx['event_id']]=append_issuer_supplements(lhx,[held(observed_at='2026-10-13T03:51:29Z'),held('LHX_sale')])
    write_workspace_generation(tmp_path/'data/company_intelligence',rows)
    return tmp_path


def rehash(owner):
    for event_id,held in owner['rows'].items():
        held['sha256']=sha256(canonical_json_bytes(held['workspace'])).hexdigest();owner['manifest']['files']['workspaces/'+event_id+'.json']['sha256']=held['sha256']
    owner['manifest_sha256']=sha256(canonical_json_bytes(owner['manifest'])).hexdigest()
    return owner


def test_adverse_and_ownership_terms_survive_closed_composition_with_owner_bindings(BASE):
    result=build_defense_economics_payload(BASE,generated_at='2026-10-13T04:40:00Z')
    assert [len(p['axes']['economics']['facts']) for p in result['profiles']]==[3,3,6,9]
    noc=result['profiles'][2];lhx=result['profiles'][3]
    assert '$68 million unfavorable' in noc['contrary_case']
    facts=lhx['axes']['economics']['facts'];assert len([f for f in facts if isinstance(f['value'],str)])==7
    assert lhx['shareholder_capture']['state']=='not_asserted'
    assert lhx['axes']['economics']['observed_at']=='2026-10-13T04:28:48Z'
    assert all(f['owner_ref'] in result['source_bindings'] and f['period'] in result['source_bindings'][f['owner_ref']]['periods'] for f in facts)
    assert all(p['axes']['recognition']['state']=='missing_owner' for p in result['profiles'])


def test_later_sale_evidence_not_admitted_before_its_actual_owner_observation(BASE):
    result=build_defense_economics_payload(BASE,generated_at='2026-10-13T04:40:00Z',as_of='2026-10-13T04:00:00Z')
    lhx=result['profiles'][3]
    assert len(lhx['axes']['economics']['facts'])==7
    assert not any(f['fact_id'].endswith(':space_business_sale_completed_terms') for f in lhx['axes']['economics']['facts'])
    assert lhx['axes']['economics']['observed_at']=='2026-10-13T03:51:29Z'


def test_hostile_rehash_cannot_relabel_prior_favorable_as_current_or_raise_adverse_amount(BASE):
    for mutation in ('period','value','basis'):
        owner=load_defense_owner_snapshot(BASE);row=owner['rows']['evt_cik0001133421_2026q2_results']['workspace']
        target=next(f for f in row['facts'] if f['metric']=='sentinel_prior_favorable_eac')
        target[mutation]={'period':'2026Q2','value':68,'basis':'issuer_reported_program_cost_estimate:SiAW:unfavorable_EAC'}[mutation]
        with pytest.raises(ValueError):build_defense_economics_payload(BASE,generated_at='2026-10-13T04:40:00Z',owner_inputs=rehash(owner))


def test_hostile_rehash_cannot_replace_exact_legal_terms_with_completed_IPO_claim(BASE):
    owner=load_defense_owner_snapshot(BASE);row=owner['rows']['evt_cik0000202058_2026q2_results']['workspace'];target=next(f for f in row['facts'] if f['metric']=='msl_qipo_conversion_terms');target['value']='IPO completed; ordinary common-shareholder capture proven.'
    with pytest.raises(ValueError,match='clause'):build_defense_economics_payload(BASE,generated_at='2026-10-13T04:40:00Z',owner_inputs=rehash(owner))


def test_hostile_rehash_fails_source_clock_document_and_rights_mismatch(BASE):
    for key,value in [('rights_profile','rp_unknown_v1'),('document_id','private_other_doc')]:
        owner=load_defense_owner_snapshot(BASE);row=owner['rows']['evt_cik0000202058_2026q2_results']['workspace'];target=next(f for f in row['facts'] if f['metric']=='msl_qipo_conversion_terms');target['source_span'][key]=value
        # Missing source association must fail, never quietly promote others.
        with pytest.raises(ValueError):build_defense_economics_payload(BASE,generated_at='2026-10-13T04:40:00Z',owner_inputs=rehash(owner))
