from pathlib import Path
from copy import deepcopy
from hashlib import sha256
import json
import pytest
from scripts.restore_event_workspace_owner import restore_event_workspace_owner
from engine.company_intelligence.event_workspace import write_workspace_generation
from engine.company_intelligence.contracts import canonical_json_bytes
from engine.government_revenue.defense_economics_producer import build_defense_economics_payload,load_defense_owner_snapshot
from tests.test_government_revenue_defense_owner_adapter import make_workspace
from tests.test_refresh_event_workspaces import _stub_dhi_revision


@pytest.fixture
def remote(tmp_path):
    rows={}
    for ticker in ('LMT','RTX','NOC','LHX'):
        row=make_workspace(ticker);rows[row['event_id']]=row
    incumbent=_stub_dhi_revision(source_available_at='2026-07-21T00:00:00Z',source_sha256='a'*64);rows[incumbent['event_id']]=incumbent
    gd=_stub_dhi_revision(event_id='evt_cik0000040533_2026q2_results',source_available_at='2026-07-29T16:01:20Z',source_sha256='b'*64);gd['issuer']['company_id']='cik:0000040533';gd['issuer']['listings']=[{'ticker':'GD','mic':'XNYS','security_id':'xnys:GD'}];gd['aliases']=['GD/2026Q2'];rows[gd['event_id']]=gd
    prefix=tmp_path/'remote';generation=write_workspace_generation(prefix,rows);raw=(generation/'manifest.json').read_bytes();manifest=json.loads(raw)
    bodies={name:(generation/name).read_bytes() for name in manifest['files']}
    return {'raw':raw,'manifest':manifest,'bodies':bodies,'event_ids':set(rows)}


def calls(remote,*,moved=False):
    count=0
    def marker(**kwargs):
        nonlocal count;count+=1
        if moved and count>1:return remote['raw']+b' ',remote['manifest']
        return remote['raw'],deepcopy(remote['manifest'])
    def manifest(generation,**kwargs):return remote['raw'],deepcopy(remote['manifest'])
    def workspace(event_id,generation,**kwargs):return remote['bodies']['workspaces/'+event_id+'.json']
    return dict(fetch_marker=marker,fetch_manifest=manifest,fetch_workspace=workspace)


def test_exact_complete_current_owner_restored_before_derived_reader_without_reacquisition(tmp_path,remote):
    root=tmp_path/'local';receipt=restore_event_workspace_owner(root,required_tickers=('LMT','RTX','NOC','LHX','GD'),**calls(remote))
    nest=root/'data/company_intelligence/event_workspaces';assert (nest/'manifest.json').read_bytes()==remote['raw']
    for name,body in remote['bodies'].items():assert (nest/'generations'/remote['manifest']['generation_id']/name).read_bytes()==body
    assert set(receipt['restored_event_ids'])==remote['event_ids'] and receipt['event_count']==6
    result=build_defense_economics_payload(root,generated_at='2026-10-13T04:40:00Z')
    assert [len(p['axes']['economics']['facts']) for p in result['profiles']]==[3,3,3,2]
    assert all(ref['content_id']==remote['manifest']['generation_id'] for ref in result['source_bindings'].values())
    assert all(ref['sha256'] in {r['sha256'] for r in remote['manifest']['files'].values()} for ref in result['source_bindings'].values())


def test_moved_marker_or_hash_mismatch_has_no_local_effect_and_preserves_prior_marker(tmp_path,remote):
    root=tmp_path/'local';nest=root/'data/company_intelligence/event_workspaces';nest.mkdir(parents=True);marker=nest/'manifest.json';marker.write_bytes(b'prior-marker')
    with pytest.raises(ValueError,match='moved'):restore_event_workspace_owner(root,**calls(remote,moved=True))
    assert marker.read_bytes()==b'prior-marker' and not (nest/'generations').exists()
    key=next(iter(remote['bodies']));remote['bodies'][key]+=b' '
    with pytest.raises(ValueError,match='receipt'):restore_event_workspace_owner(root,**calls(remote))
    assert marker.read_bytes()==b'prior-marker'


def test_marker_immutable_mismatch_absent_required_ticker_and_alias_partial_refuse(tmp_path,remote):
    bad=calls(remote);bad['fetch_manifest']=lambda generation,**kwargs:(remote['raw']+b' ',remote['manifest'])
    with pytest.raises(ValueError,match='immutable'):restore_event_workspace_owner(tmp_path/'a',**bad)
    with pytest.raises(ValueError,match='does not cover'):restore_event_workspace_owner(tmp_path/'b',required_tickers=('HII',),**calls(remote))
    remote['manifest']['aliases']['HII/2026Q2']='evt_cik0001501585_2026q2_results';remote['raw']=canonical_json_bytes(remote['manifest'])
    with pytest.raises(ValueError,match='coverage'):restore_event_workspace_owner(tmp_path/'c',**calls(remote))


def test_corrupted_immutable_local_cache_is_never_overwritten(tmp_path,remote):
    root=tmp_path/'local';restore_event_workspace_owner(root,**calls(remote));nest=root/'data/company_intelligence/event_workspaces';marker=(nest/'manifest.json').read_bytes();key=next(iter(remote['bodies']));target=nest/'generations'/remote['manifest']['generation_id']/key;target.write_bytes(b'corrupted-owner')
    with pytest.raises(ValueError,match='collision'):restore_event_workspace_owner(root,**calls(remote))
    assert target.read_bytes()==b'corrupted-owner' and (nest/'manifest.json').read_bytes()==marker


def test_semantic_noop_preserves_owner_clocks_and_derived_content_identity(tmp_path,remote):
    root=tmp_path/'local';a=restore_event_workspace_owner(root,**calls(remote));first=build_defense_economics_payload(root,generated_at='2026-10-13T04:40:00Z');b=restore_event_workspace_owner(root,**calls(remote));second=build_defense_economics_payload(root,generated_at='2026-10-13T05:40:00Z')
    assert a['manifest_sha256']==b['manifest_sha256'] and first['content_id']==second['content_id']
    assert first['source_bindings']==second['source_bindings']
