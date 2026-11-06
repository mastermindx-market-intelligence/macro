from pathlib import Path
from datetime import date
import json
from engine.company_intelligence import defense_profiles as profiles
from engine.company_intelligence.identity import IssuerRegistry
from scripts import refresh_event_workspaces as owner

FIXTURES=Path(__file__).with_name('fixtures')/'company_intelligence'/'defense'


def test_first_quartet_admission_is_current_context_then_boundary_preserves_noop(monkeypatch):
    ticker='LHX';filing=json.loads((FIXTURES/(ticker+'.filing.json')).read_text())
    row={'accessionNumber':filing['accession'],'reportDate':filing['report_date'],'acceptanceDateTime':filing['acceptance_datetime']}
    older=dict(row,accessionNumber='0000202058-25-000010',acceptanceDateTime='2025-07-01T12:00:00Z')
    monkeypatch.setattr(owner,'_fetch_submissions_candidates',lambda *a,**k:[older,row])
    seen=[]
    def resolve(r,**kwargs):
        seen.append(r['accessionNumber']);return dict(filing,exhibit_body=(FIXTURES/'LHX.segment.html').read_text())
    monkeypatch.setattr(owner,'_resolve_exhibit_for_row',resolve)
    monkeypatch.setattr(owner,'production_registry',lambda:IssuerRegistry(profiles.defense_issuer(t) for t in profiles.DEFENSE_TICKERS))
    monkeypatch.setattr(owner,'acquire_transcript_for',lambda *a,**k:(None,None))
    built=owner.discover_new_homebuilder_revisions(ticker,chain_state_loader=lambda _:[],today=date(2026,10,13))
    assert len(built)==1 and seen==[filing['accession']]
    assert built[0][1]['fiscal_period']=={'year':2026,'quarter':2,'calendar_end':None}
    assert built[0][1]['lifecycle']['source_available_at']==filing['acceptance_datetime']
    seen.clear()
    assert owner.discover_new_homebuilder_revisions(ticker,chain_state_loader=lambda _:[],discovery_boundary=filing['acceptance_datetime'],today=date(2026,10,13))==[]
    assert seen==[]


def test_quartet_source_ambiguity_does_not_default_to_apple_or_calendar_guess(monkeypatch):
    ticker='LHX';filing=json.loads((FIXTURES/(ticker+'.filing.json')).read_text());row={'accessionNumber':filing['accession'],'reportDate':filing['report_date'],'acceptanceDateTime':filing['acceptance_datetime']}
    monkeypatch.setattr(owner,'_fetch_submissions_candidates',lambda *a,**k:[row])
    body=(FIXTURES/'LHX.segment.html').read_text()
    monkeypatch.setattr(owner,'_resolve_exhibit_for_row',lambda *a,**k:dict(filing,exhibit_body=body+body))
    assert owner.discover_new_homebuilder_revisions(ticker,chain_state_loader=lambda _:[],today=date(2026,10,13))==[]


def test_newer_nonquarterly_exhibit_does_not_hide_latest_qualified_results(monkeypatch):
    filing=json.loads((FIXTURES/'RTX.filing.json').read_text())
    valid={'accessionNumber':filing['accession'],'reportDate':filing['report_date'],'acceptanceDateTime':filing['acceptance_datetime']}
    newest=dict(valid,accessionNumber='0000101829-26-000099',acceptanceDateTime='2026-10-08T12:00:00Z')
    monkeypatch.setattr(owner,'_fetch_submissions_candidates',lambda *a,**k:[valid,newest])
    seen=[]
    def resolve(row,**kwargs):
        seen.append(row['accessionNumber'])
        return dict(filing,exhibit_body='<p>Nonquarterly financing update</p>' if row is newest else (FIXTURES/'RTX.segment.html').read_text())
    monkeypatch.setattr(owner,'_resolve_exhibit_for_row',resolve)
    monkeypatch.setattr(owner,'production_registry',lambda:IssuerRegistry(profiles.defense_issuer(t) for t in profiles.DEFENSE_TICKERS))
    monkeypatch.setattr(owner,'acquire_transcript_for',lambda *a,**k:(None,None))
    result=owner.discover_new_homebuilder_revisions('RTX',chain_state_loader=lambda _:[],today=date(2026,10,13))
    assert len(result)==1 and result[0][1]['fiscal_period']['quarter']==2
    assert seen==[newest['accessionNumber'],valid['accessionNumber']]
