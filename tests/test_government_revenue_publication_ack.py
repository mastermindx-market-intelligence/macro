from __future__ import annotations
import base64
from hashlib import sha1, sha256
import importlib.util
import json
import os
from pathlib import Path
import sys
import pytest
OVERLAY=Path(os.environ.get('GRV_Q3_OVERLAY',Path.cwd()))
spec=importlib.util.spec_from_file_location('q3_publication_ack',OVERLAY/'engine/government_revenue/publication_ack.py')
ack=importlib.util.module_from_spec(spec);sys.modules[spec.name]=ack;spec.loader.exec_module(ack)
PREFIX=b'{"synthetic_whole_line":1}\n'; RAW=PREFIX+b'{"later_synthetic_line":2}\n'
COMMIT='c'*40;TREE='d'*40;HEAD='e'*40
BLOB=sha1(b'blob '+str(len(RAW)).encode()+b'\0'+RAW).hexdigest()

def fixture():
    paths={'/user':{'id':123,'login':'existing-publisher'},
        '/repos/'+ack.REPOSITORY:{'id':456,'full_name':ack.REPOSITORY},
        f'/repos/{ack.REPOSITORY}/actions/runs/789':{'id':789,'head_sha':HEAD,'path':ack.WORKFLOW,
            'repository':{'id':456,'full_name':ack.REPOSITORY},'status':'in_progress','event':'schedule'},
        f'/repos/{ack.REPOSITORY}/git/commits/{COMMIT}':{'sha':COMMIT,'tree':{'sha':TREE}},
        f'/repos/{ack.REPOSITORY}/git/trees/{TREE}?recursive=1':{'sha':TREE,'truncated':False,
            'tree':[{'path':ack.LEDGER_PATH,'sha':BLOB,'type':'blob','mode':'100644'}]},
        f'/repos/{ack.REPOSITORY}/git/blobs/{BLOB}':{'sha':BLOB,'encoding':'base64','size':len(RAW),
            'content':base64.b64encode(RAW).decode()},
        f'/repos/{ack.REPOSITORY}/git/ref/heads/main':{'ref':'refs/heads/main','object':{'type':'commit','sha':COMMIT}}}
    kw={'principal_login':'existing-publisher','principal_id':123,'repository_id':456,'run_id':789,
        'run_head_sha':HEAD,'published_commit_sha':COMMIT,'expected_ledger_prefix':PREFIX,
        'entry_session':'2026-10-14','actual_read_completed_at':lambda:'2026-10-13T23:00:02Z',
        'source_generation_sha256':'a'*64,'registration_sha256':'b'*64}
    calls=[]
    def reader(path):
        calls.append(path)
        return ack.OwnerObservation(200,{'date':'Tue, 13 Oct 2026 23:00:00 GMT'},json.dumps(paths[path]).encode())
    return paths,kw,calls,reader

def test_ack_binds_actual_current_prefix_and_requires_reproof():
    paths,kw,calls,reader=fixture();p=ack.acknowledge_published_prefix(read_owner=reader,**kw)
    assert p['ledger_prefix_sha256']==sha256(PREFIX).hexdigest()
    assert p['published_ledger_sha256']==sha256(RAW).hexdigest()
    assert p['published_commit_sha']==COMMIT and p['run_head_sha']==HEAD
    assert p['append_count']==0 and p['requires_new_final_generation_proof'] is True
    assert len(calls)==7 and calls[0]=='/user' and calls[-1].endswith('/git/ref/heads/main')
    assert ack.acknowledge_published_prefix(read_owner=reader,**kw)==p

@pytest.mark.parametrize('mutation',['principal','repo','run','run_head','workflow','inactive','commit',
    'truncated','wrong_path','wrong_blob','bytes','canonical_ref','missing_date','late','cached','unauthenticated','stale_local','malformed_nested'])
def test_hostile_observations_refuse(mutation):
    paths,kw,calls,reader=fixture();run=f'/repos/{ack.REPOSITORY}/actions/runs/789'
    tree=f'/repos/{ack.REPOSITORY}/git/trees/{TREE}?recursive=1';blob=f'/repos/{ack.REPOSITORY}/git/blobs/{BLOB}'
    if mutation=='principal':paths['/user']['login']='another-principal'
    if mutation=='repo':paths['/repos/'+ack.REPOSITORY]['full_name']='another/repo'
    if mutation=='run':paths[run]['id']=790
    if mutation=='run_head':paths[run]['head_sha']='f'*40
    if mutation=='workflow':paths[run]['path']='another-workflow.yml'
    if mutation=='inactive':paths[run]['status']='completed'
    if mutation=='commit':paths[f'/repos/{ack.REPOSITORY}/git/commits/{COMMIT}']['sha']='f'*40
    if mutation=='truncated':paths[tree]['truncated']=True
    if mutation=='wrong_path':paths[tree]['tree'][0]['path']='site/copied_ledger.jsonl'
    if mutation=='wrong_blob':paths[blob]['sha']='f'*40
    if mutation=='bytes':kw['expected_ledger_prefix']=b'{"retrospective_replacement":1}\n'
    if mutation=='canonical_ref':paths[f'/repos/{ack.REPOSITORY}/git/ref/heads/main']['object']['sha']='f'*40
    if mutation=='stale_local':kw['actual_read_completed_at']=lambda:'2026-10-14T00:00:00Z'
    if mutation=='malformed_nested':paths[run]['repository']=None
    def hostile(path):
        p=reader(path)
        if mutation=='missing_date':return ack.OwnerObservation(200,{},p.body)
        if mutation=='late':return ack.OwnerObservation(200,{'date':'Wed, 14 Oct 2026 00:00:00 GMT'},p.body)
        if mutation=='cached':return ack.OwnerObservation(200,{'date':'Tue, 13 Oct 2026 23:00:00 GMT','age':'10'},p.body)
        if mutation=='unauthenticated':return ack.OwnerObservation(401,p.headers,p.body)
        return p
    with pytest.raises(ack.AcknowledgementError):ack.acknowledge_published_prefix(read_owner=hostile,**kw)

def test_strict_conservative_budget():
    kw={'actual_now':'2026-10-13T23:50:00Z','entry_session':'2026-10-14',
        'proof_budget_seconds':300,'push_budget_seconds':200,'acknowledgement_budget_seconds':50,'safety_seconds':50}
    with pytest.raises(ack.AcknowledgementError,match='insufficient'):ack.require_remaining_window(**kw)
    kw['actual_now']='2026-10-13T23:49:59Z';assert ack.require_remaining_window(**kw)==601
    kw['proof_budget_seconds']=True
    with pytest.raises(ack.AcknowledgementError,match='budgets'):ack.require_remaining_window(**kw)

def test_author_clock_cannot_supply_server_observation():
    paths,kw,calls,reader=fixture()
    paths[f'/repos/{ack.REPOSITORY}/git/commits/{COMMIT}']['author']={'date':'2020-01-01T00:00:00Z'}
    def no_clock(path):return ack.OwnerObservation(200,{},reader(path).body)
    with pytest.raises(ack.AcknowledgementError,match='server'):ack.acknowledge_published_prefix(read_owner=no_clock,**kw)

def test_empty_and_partial_prefix_refused_before_read():
    for raw in (b'',b'partial line'):
        paths,kw,calls,reader=fixture();kw['expected_ledger_prefix']=raw
        with pytest.raises(ack.AcknowledgementError,match='whole-line'):ack.acknowledge_published_prefix(read_owner=reader,**kw)
        assert not calls

def test_transport_pinned_get_no_debug_or_credential_output(monkeypatch):
    from types import SimpleNamespace
    calls=[]
    def run(args,**kw):
        calls.append((args,kw))
        return SimpleNamespace(returncode=0,stdout=b'HTTP/2.0 200 OK\r\nDate: Tue, 13 Oct 2026 23:00:00 GMT\r\n\r\n{"id":123}',stderr=b'')
    monkeypatch.setattr(ack.subprocess,'run',run);monkeypatch.setenv('GH_DEBUG','api')
    observation=ack.GitHubOwnerReader()('/user');args,kw=calls[0]
    assert args[args.index('--hostname')+1]=='github.com' and args[args.index('--method')+1]=='GET'
    assert 'GH_DEBUG' not in kw['env'] and observation.status==200
    with pytest.raises(ack.AcknowledgementError):ack.GitHubOwnerReader()('https://lookalike.test/user')
