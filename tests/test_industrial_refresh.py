from pathlib import Path
from datetime import datetime,timezone
import json
from copy import deepcopy
import pytest
from engine.company_intelligence.industrial_sources import refresh_lhx_supplements,SOURCE_OWNER_TICKERS,SALE_URL,source_owner_profile
from tests.test_government_revenue_defense_owner_adapter import make_workspace
FIXTURES=Path(__file__).with_name('fixtures')/'company_intelligence'/'defense'


def http_fixture(url):
    if url.endswith('CIK0000202058.json'):
        return 200,json.dumps({'cik':202058,'filings':{'recent':{'accessionNumber':['0000202058-26-000058'],'form':['10-Q'],'filingDate':['2026-07-30'],'reportDate':['2026-07-03'],'acceptanceDateTime':['2026-07-30T13:06:49Z'],'primaryDocument':['hrs-20260703.htm'],'items':['']}}}).encode()
    if url==SALE_URL:return 200,(FIXTURES/'LHX.sale.html').read_bytes()
    if url.endswith('/hrs-20260703.htm'):return 200,(FIXTURES/'LHX.10Q.html').read_bytes()
    raise AssertionError(url)


def test_existing_owner_cohort_expands_to_gd_without_changing_quartet_membership():
    from engine.company_intelligence.defense_profiles import DEFENSE_TICKERS
    assert DEFENSE_TICKERS==('LMT','RTX','NOC','LHX') and SOURCE_OWNER_TICKERS==(*DEFENSE_TICKERS,'GD')
    assert source_owner_profile('NOC').ticker=='NOC' and source_owner_profile('GD').ticker=='GD'


def test_supplement_refresh_existing_workspace_preserves_ex99_clocks_and_noops_on_same_bytes():
    original=make_workspace('LHX');clock=datetime(2026,10,13,4,28,48,tzinfo=timezone.utc)
    first=refresh_lhx_supplements(original,http_get=http_fixture,now=lambda:clock)
    assert first['lifecycle']==original['lifecycle']
    assert len(first['facts'])==len(original['facts'])+7
    second=refresh_lhx_supplements(first,http_get=http_fixture,prior=first,now=lambda:datetime(2026,10,14,4,28,48,tzinfo=timezone.utc))
    assert second==first


def test_source_revision_qualifies_new_bytes_and_links_existing_document_owner():
    clock=datetime(2026,10,13,4,28,48,tzinfo=timezone.utc);first=refresh_lhx_supplements(make_workspace('LHX'),http_get=http_fixture,now=lambda:clock)
    def changed(url):
        status,raw=http_fixture(url)
        if url==SALE_URL:raw=raw.replace(b'$845',b'$999')
        return status,raw
    later=datetime(2026,10,14,4,28,48,tzinfo=timezone.utc)
    second=refresh_lhx_supplements(first,http_get=changed,prior=first,now=lambda:later)
    old=next(s for s in first['sources'] if s.get('supplement_profile')=='LHX_sale')
    new=next(s for s in second['sources'] if s.get('supplement_profile')=='LHX_sale')
    assert new['document_id']!=old['document_id']
    assert new['source_document']['revision']==2 and new['source_document']['supersedes_document_id']==old['document_id']
    assert new['source_clock']['observed_at']=='2026-10-14T04:28:48Z'
    assert any('$845' in f.get('value','') for f in first['facts'] if isinstance(f.get('value'),str))
    assert any('$999' in f.get('value','') for f in second['facts'] if isinstance(f.get('value'),str))
    third=refresh_lhx_supplements(second,http_get=changed,prior=second,now=lambda:later)
    assert third==second


def test_different_fiscal_period_or_issuer_never_reuses_q2_supplements():
    row=make_workspace('LMT');assert refresh_lhx_supplements(row,http_get=lambda u:pytest.fail('network'))==row
    row=make_workspace('LHX');row['fiscal_period']['quarter']=3
    assert refresh_lhx_supplements(row,http_get=lambda u:pytest.fail('network'))==row
