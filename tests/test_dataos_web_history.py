"""Existing Data & Lab transport keeps its descriptor-confined source access."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import pytest
from lib.dataos.web_workspace import DataWorkspace,RootBinding,WorkspaceError
from lib.dataos.web_api import dispatch
from tests.test_market_memory_history_archive import make_archive
from tests.test_market_memory_history_dossier import macro

@pytest.fixture
def case(monkeypatch,tmp_path):
    ar,root,r=make_archive(monkeypatch,tmp_path)
    registry=tmp_path/'registry.yml';registry.write_text('schema: dataset_registry.v1\ndatasets: []\n')
    ws=DataWorkspace((RootBinding('fixture',tmp_path,'research_capture'),),registry,source_revision='a'*40)
    return SimpleNamespace(ws=ws,root=root,receipt=r,base=tmp_path,ar=ar,config=tmp_path/'host.json')

def query(case,**changes):
    q={'action':'history_dossier','ref':'fixture:history/manifest.json','manifest_sha256':case.receipt['manifest_sha256'],'date':'2020-01-05'}
    q.update(changes);return q

def test_existing_transport_exposes_hash_bound_daily_dossier(case):
    result=dispatch(case.ws,query(case),config_path=case.config)
    assert result['action']=='history_dossier'
    assert result['result']['market']['rows'][0]['close_tradj']==52.0
    assert result['source_access']=='read_only'
    assert result['implementation_revision']=='a'*40
    assert len(result['source_files'])==2
    assert all(r['content_sha256'] for r in result['source_files'])
    assert len(result['query_receipt_sha256'])==64
    assert 'outcomes' not in result['result']['market']

def test_history_capability_is_explicit_not_a_new_transport(case):
    result=dispatch(case.ws,{'action':'capabilities'},config_path=case.config)
    assert 'history_dossier' in result['actions']
    assert result['history']['source_access']=='existing_descriptor_confined_roots'
    assert result['history']['point_in_time_eligible'] is False

def test_bare_filesystem_reader_is_never_used_by_transport(case,monkeypatch):
    from engine.neuralweb import market_memory_history_macro as mm
    def forbidden(*a,**k):pytest.fail('transport must use existing descriptor-confined file owner')
    mp,mh=macro(case.base)
    monkeypatch.setattr(case.ar,'_regular_file',forbidden)
    monkeypatch.setattr(mm,'_regular_file',forbidden)
    result=dispatch(case.ws,query(case,date='2020-02-13',macro_ref='fixture:macro.json',macro_sha256=mh),config_path=case.config)
    assert result['result']['macro']['total_events']==1
    assert result['result']['market']['status']=='NO_OBSERVATION'

def test_default_transport_does_not_open_outcome_file(case):
    for p in case.root.glob('outcomes-*.parquet'):p.unlink()
    assert dispatch(case.ws,query(case),config_path=case.config)['result']['market']['rows']
    with pytest.raises(WorkspaceError):dispatch(case.ws,query(case,reveal_outcomes=True),config_path=case.config)

def test_explicit_reveal_stays_explicit(case):
    r=dispatch(case.ws,query(case,reveal_outcomes=True),config_path=case.config)
    assert r['result']['outcomes_revealed'] is True
    assert r['result']['market']['outcomes']

@pytest.mark.parametrize('change',[
    {'ref':'fixture:../outside/manifest.json'},
    {'ref':'unbound:history/manifest.json'},
    {'ref':'fixture:history/secret-manifest.json'},
    {'ref':'fixture:history/states-2020.parquet'},
    {'manifest_sha256':'bad'}, {'reveal_outcomes':'false'},
    {'macro_ref':'fixture:macro.json'},
    {'macro_sha256':'a'*64}, {'date':'2020-1-5'},
])
def test_unsafe_history_requests_are_refused(case,change):
    with pytest.raises(WorkspaceError):dispatch(case.ws,query(case,**change),config_path=case.config)

@pytest.mark.parametrize('field',['command','sql','output','root','api_key','pit_backtest_eligible'])
def test_no_write_or_provider_arguments_are_admitted(case,field):
    with pytest.raises(WorkspaceError,match='INVALID_REQUEST_FIELDS'):
        dispatch(case.ws,query(case,**{field:'not-admitted'}),config_path=case.config)

def test_symlink_and_hardlink_data_refused_by_original_owner(case):
    target=next(case.root.glob('states-*.parquet'));data=target.read_bytes();target.unlink()
    other=case.base/'outside.parquet';other.write_bytes(data);target.symlink_to(other)
    with pytest.raises(WorkspaceError):dispatch(case.ws,query(case),config_path=case.config)
    target.unlink();os.link(other,target)
    with pytest.raises(WorkspaceError):dispatch(case.ws,query(case),config_path=case.config)

def test_changed_source_version_during_read_refuses_before_return(case,monkeypatch):
    original=case.ws._file
    @contextmanager
    def changed(ref,*args,**kwargs):
        with original(ref,*args,**kwargs) as opened:
            yield opened
            if ref.endswith('states-2020.parquet'):
                p=case.root/'states-2020.parquet';p.write_bytes(p.read_bytes()+b'changed')
    monkeypatch.setattr(case.ws,'_file',changed)
    with pytest.raises(WorkspaceError,match='SOURCE_CHANGED'):
        dispatch(case.ws,query(case),config_path=case.config)

def test_no_files_written_by_history_request(case):
    before={str(p.relative_to(case.base)):(p.stat().st_mtime_ns,hashlib.sha256(p.read_bytes()).hexdigest()) for p in case.base.rglob('*') if p.is_file()}
    dispatch(case.ws,query(case),config_path=case.config)
    after={str(p.relative_to(case.base)):(p.stat().st_mtime_ns,hashlib.sha256(p.read_bytes()).hexdigest()) for p in case.base.rglob('*') if p.is_file()}
    assert before==after
