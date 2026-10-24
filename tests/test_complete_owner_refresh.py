from pathlib import Path
import json
from tests.test_refresh_event_workspaces import _FakeR2,_refresh,_stub_dhi_revision,FLAGSHIP_EVENT_ID
from tests.test_government_revenue_defense_owner_adapter import make_workspace
from engine.company_intelligence import industrial_sources


def test_every_owner_generation_carries_all_incumbent_and_quartet_gd_slots_before_first_publish(tmp_path,monkeypatch):
    current={};hb={'DHI':'0000882184','PHM':'0000822416','KBH':'0000795266','TOL':'0000794170'}
    for ticker,cik in {**hb,'GD':'0000040533'}.items():
        row=_stub_dhi_revision(event_id=f'evt_cik{cik}_2026q2_results',source_available_at='2026-07-01T00:00:00Z',source_sha256='a'*64)
        row['issuer']['company_id']='cik:'+cik;row['sources'][0]['filing_key']['cik']=cik;current[ticker]=row
    for ticker in ('LMT','RTX','NOC','LHX'):current[ticker]=make_workspace(ticker)
    monkeypatch.setattr(industrial_sources,'refresh_lhx_supplements',lambda row,**k:row)
    seen=[]
    def carry(ticker):seen.append(ticker);return current.get(ticker)
    trigger=_stub_dhi_revision(source_available_at='2026-07-21T00:00:00Z',source_sha256='b'*64)
    def discover(ticker,**kwargs):return [(trigger['event_id'],trigger)] if ticker=='DHI' else []
    assert _refresh(tmp_path,_FakeR2(),homebuilder_carry_forward_loader=carry,homebuilder_discovery=discover)==0
    assert set(seen)==set(current)
    generations=list((tmp_path/'event_workspaces/generations').iterdir());assert generations
    required={FLAGSHIP_EVENT_ID,*(row['event_id'] for row in current.values())}
    for path in generations:
        manifest=json.loads((path/'manifest.json').read_text())
        assert required<={name.split('/')[-1].removesuffix('.json') for name in manifest['files']}
