from pathlib import Path
from copy import deepcopy
import json
from hashlib import sha256
import pytest
from engine.company_intelligence.issuer_supplements import build_issuer_supplement,validate_supplement_source,append_issuer_supplements
from engine.company_intelligence.event_workspace import write_workspace_generation,validate_generation_clocks
from tests.test_government_revenue_defense_owner_adapter import make_workspace

FIXTURES=Path(__file__).with_name('fixtures')/'company_intelligence'/'defense'
FILING={'cik':'0000202058','accession':'0000202058-26-000058','form':'10-Q','filing_date':'2026-07-30','acceptance_datetime':'2026-07-30T13:06:49Z','report_date':'2026-07-03','primary_document':'hrs-20260703.htm'}
URL='https://www.sec.gov/Archives/edgar/data/202058/000020205826000058/hrs-20260703.htm'
SALE_URL='https://investors.l3harris.com/news/news-details/2026/L3Harris-Completes-Sale-of-Majority-Stake-in-Commercial-Space-Propulsion-Power-and-Electronics-Businesses-to-AE-Industrial-Partners/default.aspx'


def held(kind='LHX_10Q',mutate=lambda x:x,**overrides):
    name='10Q' if kind=='LHX_10Q' else 'sale';body=mutate((FIXTURES/f'LHX.{name}.html').read_bytes().decode())
    observed='2026-10-13T04:28:48Z'
    args=dict(kind=kind,body=body,url=URL if name=='10Q' else SALE_URL,filing=deepcopy(FILING) if name=='10Q' else None,event_id='evt_cik0000202058_2026q2_results',period='2026Q2' if name=='10Q' else '2026-08-04',observed_at=observed,source_available_at=FILING['acceptance_datetime'] if name=='10Q' else observed,expected_sha256=sha256(body.encode()).hexdigest())
    args.update(overrides);return build_issuer_supplement(**args)


def test_native_10q_and_issuer_publication_keep_distinct_identity_availability_basis():
    q,sale=held(),held('LHX_sale')
    validate_supplement_source(q['source'],event_id=q['facts'][0]['event_id']);validate_supplement_source(sale['source'],event_id=sale['facts'][0]['event_id'])
    assert q['source']['filing_key']=={'cik':'0000202058','accession':'0000202058-26-000058'}
    assert sale['source']['filing_key'] is None and sale['source']['form'] is None
    assert q['source']['document_id']!=sale['source']['document_id']
    assert sale['source']['source_document']['published_at'] is None
    assert sale['source']['source_clock']['available_at']==sale['source']['source_clock']['observed_at']


def test_preferred_conditional_terms_and_net_total_sale_basis_remain_explicit():
    q=held();sale=held('LHX_sale');facts={f['metric']:f for f in q['facts']+sale['facts']}
    assert '7% cumulative annual dividends, compounded quarterly' in facts['msl_preferred_payout_terms']['value']
    assert facts['msl_qipo_conversion_terms']['fact_class']=='company_forward'
    assert 'Upon completion of a QIPO' in facts['msl_qipo_conversion_terms']['value'] and '20% discount' in facts['msl_qipo_conversion_terms']['value']
    assert 'net enterprise value of $825 million' in facts['space_business_sale_pending_terms']['value']
    assert 'total enterprise value of $845 million' in facts['space_business_sale_completed_terms']['value']
    assert 'RS-25' in facts['space_business_sale_retained_scope']['value'] and '~40%' in facts['space_business_sale_retained_scope']['value']
    assert facts['space_business_sale_pending_terms']['basis']!=facts['space_business_sale_completed_terms']['basis']


def test_wrong_body_native_accession_origin_or_period_does_not_admit():
    with pytest.raises(ValueError,match='hash'):held(expected_sha256='0'*64)
    with pytest.raises(ValueError,match='native_url'):held(filing=dict(FILING,accession='0000202058-26-000059'))
    with pytest.raises(ValueError,match='form'):held(filing=dict(FILING,form='8-K'))
    with pytest.raises(ValueError,match='period'):held(period='2025Q2')
    with pytest.raises(ValueError,match='mismatch'):held(url=URL.replace('www.sec.gov','sec.example.com'))


def test_issuer_publication_cannot_borrow_SEC_clock_or_a_filing_key():
    with pytest.raises(ValueError,match='unproved'):held('LHX_sale',source_available_at='2026-08-04T00:00:00Z')
    with pytest.raises(ValueError,match='not_native'):held('LHX_sale',filing=FILING)


def test_append_keeps_original_ex99_lifecycle_and_generation_covers_newdoc_observation(tmp_path):
    base=make_workspace('LHX');original=deepcopy(base['lifecycle']);q,sale=held(),held('LHX_sale')
    row=append_issuer_supplements(base,[q,sale]);assert row['lifecycle']==original
    generation=write_workspace_generation(tmp_path/'company_intelligence',{row['event_id']:row})
    manifest=json.loads((generation/'manifest.json').read_text());published=json.loads((generation/'workspaces'/f'{row["event_id"]}.json').read_text())
    assert manifest['generated_at']=='2026-10-13T04:28:48Z'
    assert manifest['source_clock']=='2026-10-13T04:28:48Z'
    assert published['lifecycle']==original
    assert len([f for f in published['facts'] if f.get('unit')=='source_reported_terms'])==7
    broken=deepcopy(manifest);broken['generated_at']=original['observed_at'];published['generated_at']=broken['generated_at']
    with pytest.raises(ValueError,match='supplemental'):validate_generation_clocks(broken,{row['event_id']:published})


def test_first_observation_preserved_for_same_supplement_and_duplicate_event_refused():
    q=held();again=held(observed_at='2026-10-14T04:28:48Z',prior=q['source'])
    assert q['source']['source_clock']==again['source']['source_clock']
    sale=held('LHX_sale');sale_again=held('LHX_sale',observed_at='2026-10-14T04:28:48Z',source_available_at='2026-10-14T04:28:48Z',prior=sale['source'])
    assert sale_again['source']['source_clock']==sale['source']['source_clock']
    base=make_workspace('LHX')
    with pytest.raises(ValueError,match='duplicate'):append_issuer_supplements(base,[q,q])
    broken=deepcopy(q);broken['source']['source_document']['event_id']='evt_cik0000101829_2026q2_results'
    with pytest.raises(ValueError,match='event'):append_issuer_supplements(base,[broken])
