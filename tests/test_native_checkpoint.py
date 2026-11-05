"""Engine checkpoint inputs survive queue integration and squash publication."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import sys

import pytest

from scripts.ci import native_checkpoint as checkpoint


def git(root,*args):
    return subprocess.run(['git','-C',str(root),*args],capture_output=True,check=True).stdout


def commit(root,path,body):
    file=root/path;file.parent.mkdir(parents=True,exist_ok=True);file.write_text(body)
    git(root,'add','.');git(root,'commit','-qm','fixture')
    return git(root,'rev-parse','HEAD').decode().strip()


@pytest.fixture
def repo(tmp_path):
    git(tmp_path,'init','-q','-b','main');git(tmp_path,'config','user.name','fixture')
    git(tmp_path,'config','user.email','fixture@example.invalid')
    commit(tmp_path,'site/prophet/index.json','old')
    commit(tmp_path,'data/prophet/plan_corrections.jsonl','original correction\n')
    commit(tmp_path,'data/prophet_stage_shadow/ledger.jsonl','old stage\n')
    return tmp_path


@pytest.mark.parametrize('profile,path',[
    ('leader','site/anticipationdata/us_leader_pullback.json'),
    ('prophet','site/prophet/index.json'),
    ('shadow','data/prophet_stage_shadow/ledger.jsonl'),
])
def test_actual_group_preserves_original_generation_over_unrelated_main(repo,profile,path):
    base=git(repo,'rev-parse','HEAD').decode().strip();git(repo,'checkout','-qb','candidate')
    candidate=commit(repo,path,'new generation\n');git(repo,'checkout','-qb','selected',base)
    group_base=commit(repo,'unrelated','new main\n');git(repo,'merge','--no-ff','--no-edit',candidate)
    group=git(repo,'rev-parse','HEAD').decode().strip()
    result=checkpoint.validate_native_group(repo,candidate,group_base,group,profile)
    assert result['candidate']==candidate and result['checkpoint_base']==base


def test_correction_only_movement_refuses_even_without_output_conflict(repo):
    base=git(repo,'rev-parse','HEAD').decode().strip();git(repo,'checkout','-qb','candidate')
    candidate=commit(repo,'site/prophet/index.json','new index')
    git(repo,'checkout','-qb','selected',base)
    group_base=commit(repo,'data/prophet/plan_corrections.jsonl','new correction\n')
    git(repo,'merge','--no-ff','--no-edit',candidate)
    group=git(repo,'rev-parse','HEAD').decode().strip()
    with pytest.raises(checkpoint.native.PublicationHeld,match='inputs_advanced'):
        checkpoint.validate_native_group(repo,candidate,group_base,group,'prophet')


def test_group_cannot_introduce_a_different_authority_projection(repo):
    git(repo,'checkout','-qb','candidate');candidate=commit(repo,'site/prophet/index.json','new index')
    base=git(repo,'rev-parse','HEAD^').decode().strip()
    group=commit(repo,'data/prophet/plan_corrections.jsonl','injected correction\n')
    with pytest.raises(checkpoint.native.PublicationHeld,match='changed_checkpoint_projection'):
        checkpoint.validate_native_group(repo,candidate,base,group,'prophet')


@pytest.mark.parametrize('change',['delete','executable','correction'])
def test_candidate_cannot_delete_change_mode_or_publish_correction_inputs(repo,change):
    base=git(repo,'rev-parse','HEAD').decode().strip()
    if change=='delete':git(repo,'rm','site/prophet/index.json')
    elif change=='executable':
        (repo/'site/prophet/index.json').chmod(0o755);git(repo,'add','site/prophet/index.json')
    else:
        (repo/'data/prophet/plan_corrections.jsonl').write_text('changed correction\n');git(repo,'add','.')
    git(repo,'commit','-qm','refused candidate');candidate=git(repo,'rev-parse','HEAD').decode().strip()
    with pytest.raises(checkpoint.native.PublicationHeld):
        checkpoint.validate_native_group(repo,candidate,base,candidate,'prophet')


def test_original_budget_and_read_refusal_cannot_fallback(repo):
    candidate=commit(repo,'site/prophet/index.json','new index');base=git(repo,'rev-parse','HEAD^').decode().strip()
    calls=[]
    def reader(root,*args,timeout):
        calls.append((args,timeout));raise RuntimeError('original core read budget exhausted')
    for options in ({'git_read':reader},{'git_read':reader,'deadline':time.monotonic()-1}):
        with pytest.raises(checkpoint.native.PublicationHeld,match='deadline'):
            checkpoint.validate_native_group(repo,candidate,base,candidate,'prophet',**options)
    assert calls==[]
    with pytest.raises(RuntimeError,match='budget exhausted'):
        checkpoint.validate_native_group(repo,candidate,base,candidate,'prophet',
                                         git_read=reader,deadline=time.monotonic()+1)
    assert len(calls)==1 and 0<calls[0][1]<=1


def test_prophet_consumer_receives_actual_squash_and_not_source_head(repo,monkeypatch):
    candidate=commit(repo,'site/prophet/index.json','new index');base=git(repo,'rev-parse','HEAD^').decode().strip()
    tree=git(repo,'rev-parse',candidate+'^{tree}').decode().strip()
    merge=git(repo,'commit-tree',tree,'-p',base,'-m','real squash').decode().strip()
    assert merge!=candidate
    # The fake API provides immutable server object identities only. The hash
    # check below uses the REAL original candidate's local Git blob.
    def server_tree(api,identity,paths):
        result={}
        for p in paths:
            row=git(repo,'ls-tree',identity,'--',p).decode().strip().split()
            if row:result[p]={'mode':row[0],'type':row[1],'sha':row[2],'path':p}
        return result,tree
    monkeypatch.setattr(checkpoint.native,'tree',server_tree)
    receipt={'source_head':candidate,'merge_sha':merge,'observed_target_sha':merge}
    output=checkpoint.prophet_outputs(None,repo,receipt,hashlib.sha256(b'new index').hexdigest())
    assert output=={'r2_ready':'true','checkpoint_sha':merge,
                    'index_sha256':hashlib.sha256(b'new index').hexdigest()}
    with pytest.raises(checkpoint.native.PublicationHeld,match='digest_changed'):
        checkpoint.prophet_outputs(None,repo,receipt,'0'*64)
    changed=commit(repo,'data/prophet/plan_corrections.jsonl','overtaken\n')
    with pytest.raises(checkpoint.native.PublicationHeld,match='authority_superseded'):
        checkpoint.prophet_outputs(None,repo,{**receipt,'observed_target_sha':changed},hashlib.sha256(b'new index').hexdigest())


@pytest.mark.parametrize('change',['none','new-commit','dirty','wrong-branch'])
def test_original_cleanup_reclaims_only_unchanged_clean_published_candidate(repo,tmp_path,change):
    runner=tmp_path/'runner';runner.mkdir();root=runner/'prophet-checkpoint.FIXTURE1';root.mkdir()
    tree=root/'tree';branch='_prophet_checkpoint_123_1'
    git(repo,'worktree','add','-b',branch,str(tree),'HEAD')
    candidate=commit(tree,'site/prophet/index.json','published generation')
    record=tmp_path/'original.json';record.write_text(json.dumps({'producer_origin':{'published_source_head':candidate}}))
    if change=='new-commit':commit(tree,'site/prophet/index.json','new writer')
    if change=='dirty':(tree/'site/prophet/index.json').write_text('unfinished writer')
    if change=='wrong-branch':git(tree,'branch','-m','different-writer')
    body=(Path(__file__).resolve().parents[1]/'scripts/ci/native_checkpoint_settle.sh').read_text().split("<<'PYCLEAN'\n",1)[1].split('\nPYCLEAN',1)[0]
    result=subprocess.run([sys.executable,'-I','-',str(record),str(root),str(tree),branch],input=body,
        capture_output=True,text=True,env={**os.environ,'RUNNER_TEMP':str(runner),'GITHUB_WORKSPACE':str(repo),
                                          'GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'1'})
    if change=='none':
        assert result.returncode==0 and not root.exists(),result.stderr
        assert subprocess.run(['git','-C',str(repo),'show-ref','--verify','refs/heads/'+branch],capture_output=True).returncode!=0
    else:assert result.returncode==76 and tree.exists()
