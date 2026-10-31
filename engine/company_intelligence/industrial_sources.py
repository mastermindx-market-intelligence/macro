"""Existing Event Workspace refresh cohort dispatch and bounded supplements."""
from copy import deepcopy
from datetime import datetime,timezone
from hashlib import sha256
import json
from engine.company_intelligence.defense_profiles import DEFENSE_TICKERS,defense_issuer,defense_profile,source_fiscal_period
from engine.company_intelligence.gd_profile import gd_issuer,gd_profile,gd_fiscal_period
from engine.company_intelligence.noc_adverse_profile import noc_adverse_profile
from engine.company_intelligence.issuer_supplements import build_issuer_supplement,append_issuer_supplements,validate_supplement_source
from engine.earnings_release.binding import normalize_acceptance

SOURCE_OWNER_TICKERS=(*DEFENSE_TICKERS,'GD')
SALE_URL='https://investors.l3harris.com/news/news-details/2026/L3Harris-Completes-Sale-of-Majority-Stake-in-Commercial-Space-Propulsion-Power-and-Electronics-Businesses-to-AE-Industrial-Partners/default.aspx'


def source_owner_issuer(ticker):return gd_issuer() if ticker=='GD' else defense_issuer(ticker)
def source_owner_profile(ticker):return gd_profile() if ticker=='GD' else noc_adverse_profile() if ticker=='NOC' else defense_profile(ticker)
def source_owner_fiscal_period(bound,ticker):return gd_fiscal_period(bound) if ticker=='GD' else source_fiscal_period(bound,ticker)


def refresh_lhx_supplements(workspace,*,http_get,prior=None,now=None):
    """Acquire through incumbent refresh HTTP grant, before owner publication.

    A bounded qualified 2026Q2 supplemental profile; unknown future schema is
    refused/carry-forward by the caller rather than interpreted as current.
    No Government Revenue render or reader calls this function.
    """
    if workspace['issuer']['company_id']!='cik:0000202058':return workspace
    if workspace['fiscal_period']['year']!=2026 or workspace['fiscal_period']['quarter']!=2:return workspace
    from scripts.refresh_event_workspaces import submissions_rows
    status,raw=http_get('https://data.sec.gov/submissions/CIK0000202058.json')
    if status!=200:raise ValueError('LHX_supplement_submissions_unavailable')
    payload=json.loads(raw)
    if str(payload.get('cik')).lstrip('0')!='202058':raise ValueError('LHX_supplement_native_subject_mismatch')
    candidates=[r for r in submissions_rows(payload,block='recent') if r.get('form')=='10-Q']
    candidates.sort(key=lambda r:normalize_acceptance(r.get('acceptanceDateTime')),reverse=True)
    old=prior or workspace
    old_sources={s.get('supplement_profile'):s for s in old.get('sources',[]) if s.get('kind')=='issuer_supplement'}
    observed=(now() if now else datetime.now(timezone.utc))
    if isinstance(observed,datetime):observed=observed.isoformat()
    selected=None
    for row in candidates:
        # The native Q2 report ends 2026-07-03; source profile additionally
        # verifies its explicit For Second Quarter 2026 label and native URL.
        if row.get('reportDate')!='2026-07-03':continue
        accession=row['accessionNumber'];primary=row['primaryDocument']
        if '/' in primary or '..' in primary:raise ValueError('supplement_native_document_path_invalid')
        url=f'https://www.sec.gov/Archives/edgar/data/202058/{accession.replace("-","")}/{primary}'
        status,raw=http_get(url)
        if status!=200:raise ValueError('LHX_10Q_body_unavailable')
        filing={'cik':'0000202058','accession':accession,'form':row['form'],'filing_date':row['filingDate'],'acceptance_datetime':normalize_acceptance(row['acceptanceDateTime']),'report_date':row['reportDate'],'primary_document':primary}
        selected=build_issuer_supplement(kind='LHX_10Q',body=raw.decode('utf-8'),url=url,filing=filing,event_id=workspace['event_id'],period='2026Q2',observed_at=observed,source_available_at=filing['acceptance_datetime'],expected_sha256=sha256(raw).hexdigest(),prior=old_sources.get('LHX_10Q'))
        break
    if selected is None:raise ValueError('LHX_qualified_10Q_supplement_missing')
    status,raw=http_get(SALE_URL)
    if status!=200:raise ValueError('LHX_sale_stage_body_unavailable')
    sale=build_issuer_supplement(kind='LHX_sale',body=raw.decode('utf-8'),url=SALE_URL,filing=None,event_id=workspace['event_id'],period='2026-08-04',observed_at=observed,source_available_at=observed,expected_sha256=sha256(raw).hexdigest(),prior=old_sources.get('LHX_sale'))
    # Replace exactly these profile slots in CURRENT view; immutable prior
    # generations retain previous bytes and first observations. New/changed
    # document identity is qualified again by the same SourceDocument owner
    # and linked via its existing revision/supersedes fields.
    output=deepcopy(workspace);profiles={'LHX_10Q','LHX_sale'}
    removed={s.get('document_id') for s in output['sources'] if s.get('supplement_profile') in profiles}
    output['sources']=[s for s in output['sources'] if s.get('document_id') not in removed]
    output['facts']=[f for f in output['facts'] if (f.get('source_span') or {}).get('document_id') not in removed]
    output=append_issuer_supplements(output,[selected,sale])
    return output
