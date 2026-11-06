"""Canonical Asia integration after the Fabric leaf's prelaunch admission stop.

No worker artifact or identity is adopted. HTTP publication is a test fake;
real wrapper/Git state and original source graph are exercised below.
"""
import os
from pathlib import Path
import subprocess

import pytest
import yaml

from scripts.ci import native_queue_push as native
from scripts.workflow_run_source import resolve_run_source

ROOT=Path(__file__).resolve().parents[1]


def git(root,*args):
    return subprocess.run(['git','-C',str(root),*args],capture_output=True,check=True,text=True).stdout.strip()


@pytest.mark.parametrize('job,step',[('asia','native_publication_stage'),
    ('asia','native_publication_engine_stage'),('ths_rescrape','native_publication_stage')])
def test_actual_asia_source_tuple_stays_separate_by_job_and_generation(monkeypatch,job,step):
    env={'GITHUB_REPOSITORY':native.REPOSITORY,'GITHUB_REF':'refs/heads/main','GITHUB_JOB':job,
        'GITHUB_WORKFLOW_REF':native.REPOSITORY+'/.github/workflows/asia-close.yml@refs/heads/main',
        'GITHUB_WORKFLOW_SHA':'1'*40,'GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'1',
        'NATIVE_PUBLICATION_TOKEN_ORIGIN':'GITHUB_TOKEN','NATIVE_PUBLICATION_PUBLISHING_STEP':step}
    for k,v in env.items():monkeypatch.setenv(k,v)
    locator,workflow,_=native.producer_identity('2'*40,'3'*64)
    assert workflow=='.github/workflows/asia-close.yml' and locator['job']==job and locator['step']==step
    monkeypatch.setenv('NATIVE_PUBLICATION_PUBLISHING_STEP','native_publication_unknown_stage')
    with pytest.raises(native.PublicationHeld):native.producer_identity('2'*40,'3'*64)


@pytest.mark.parametrize('script',['asia_native_data.sh','asia_native_ths.sh'])
@pytest.mark.parametrize('status',[77,75,76])
def test_real_stage_wrapper_never_rebases_or_falls_back_after_pending_or_unknown(tmp_path,script,status):
    repo=tmp_path/'repo';repo.mkdir();git(repo,'init','-q','-b','main')
    git(repo,'config','user.name','fixture');git(repo,'config','user.email','fixture@example.invalid')
    data=repo/'data/baskets_china_ths/value.json';data.parent.mkdir(parents=True);data.write_text('original')
    git(repo,'add','.');git(repo,'commit','-qm','original source')
    if script=='asia_native_ths.sh':data.write_text('new generation')
    else:
        data.write_text('new generation');git(repo,'add','.');git(repo,'commit','-qm','already committed collection')
    helper=repo/'scripts/ci/push_retry.sh';helper.parent.mkdir(parents=True)
    helper.write_text((ROOT/'scripts/ci/push_retry.sh').read_text()+'''
push_native_do() { return "$TEST_NATIVE_STATUS"; }
push_attempt() { echo FORBIDDEN_LEGACY_RETRY >> "$TEST_EFFECTS"; return 1; }
push_abort_rebase() { echo FORBIDDEN_CLEANUP >> "$TEST_EFFECTS"; }
''')
    runner=tmp_path/'runner';runner.mkdir();output=tmp_path/'out';effects=tmp_path/'effects'
    result=subprocess.run(['bash',str(ROOT/'scripts/ci'/script)],cwd=repo,capture_output=True,text=True,
        env={**os.environ,'GITHUB_REPOSITORY':'fixture-only','GITHUB_WORKSPACE':str(repo),
            'RUNNER_TEMP':str(runner),'GITHUB_OUTPUT':str(output),
            'TEST_NATIVE_STATUS':str(status),'TEST_EFFECTS':str(effects)})
    assert result.returncode==(0 if status==77 else status),result.stdout+result.stderr
    assert not effects.exists()
    assert data.read_text()=='new generation'
    assert (output.read_text() if output.exists() else '')==('publication=pending\n' if status==77 else '')


def test_stage_upload_final_graph_preserves_source_consumer_ids_and_original_budget():
    doc=yaml.safe_load((ROOT/'.github/workflows/asia-close.yml').read_text())
    assert doc['permissions']['pull-requests']=='write'
    for job,stage,final in [('asia','native_publication_stage','pushdata'),
        ('asia','native_publication_engine_stage','native_publication_engine'),
        ('ths_rescrape','native_publication_stage','native_publication')]:
        steps=doc['jobs'][job]['steps'];byid={s['id']:s for s in steps if s.get('id')}
        ids=[stage,stage+'_origin',final];indices=[steps.index(byid[k]) for k in ids]
        assert indices==list(range(indices[0],indices[0]+3))
        origin=byid[stage+'_origin'];assert origin['uses']=='actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02'
        assert origin['with']['overwrite'] is False and origin['with']['if-no-files-found']=='error'
        assert stage+'_origin.outcome' in byid[final]['if']
        assert byid[final]['env']['NATIVE_PUBLICATION_PUBLISHING_STEP']==stage
        assert 'native_checkpoint_settle.sh' in byid[final]['run']
        source=resolve_run_source(byid[stage]['run'],ROOT)
        assert source.index('native_publication_prepare_source')<source.index('push_native_do')<source.index('while push_attempt')
        assert 'PUSH_BUDGET_SECS=600' in source if stage=='native_publication_engine_stage' else 'PUSH_BUDGET_SECS=' not in source
    # The original carve/park proof still decides whether data publication runs.
    steps=doc['jobs']['asia']['steps'];byid={s['id']:s for s in steps if s.get('id')}
    assert 'steps.park.outputs.parked' in byid['native_publication_stage']['if']
    local=resolve_run_source(byid['commitdata']['run'],ROOT)
    assert local.index('native_publication_prepare_source')<local.index('options_signal_nightly.sh')
    assert 'qledger_withheld=true' in local and 'qledger_snapshot=' in local


@pytest.mark.parametrize('script',['asia_native_data.sh','asia_native_ths.sh'])
def test_affirmative_native_off_preserves_the_original_guarded_legacy_publication(tmp_path,script):
    remote=tmp_path/'remote';remote.mkdir();git(remote,'init','-q','--bare')
    repo=tmp_path/'repo';repo.mkdir();git(repo,'init','-q','-b','main')
    git(repo,'config','user.name','fixture');git(repo,'config','user.email','fixture@example.invalid')
    data=repo/'data/baskets_china_ths/value.json';data.parent.mkdir(parents=True);data.write_text('original')
    git(repo,'add','.');git(repo,'commit','-qm','original');git(repo,'remote','add','origin',str(remote));git(repo,'push','origin','main')
    data.write_text('new generation')
    if script=='asia_native_data.sh':git(repo,'add','.');git(repo,'commit','-qm','collected generation')
    helper=repo/'scripts/ci/push_retry.sh';helper.parent.mkdir(parents=True)
    helper.write_text('. '+__import__('shlex').quote(str(ROOT/'scripts/ci/push_retry.sh'))+'\n'+'''
push_native_do() { return 80; }
push_do() { [ "$NATIVE_PUBLICATION_EXPECT_OFF" = 1 ] || return 76; git push origin HEAD:main; }
''')
    runner=tmp_path/'runner';runner.mkdir();output=tmp_path/'output'
    result=subprocess.run(['bash',str(ROOT/'scripts/ci'/script)],cwd=repo,capture_output=True,text=True,
        env={**os.environ,'GITHUB_REPOSITORY':'fixture-only','GITHUB_WORKSPACE':str(repo),
            'RUNNER_TEMP':str(runner),'GITHUB_OUTPUT':str(output),
            'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(ROOT)})
    assert result.returncode==0,result.stdout+result.stderr
    assert git(repo,'show','HEAD:data/baskets_china_ths/value.json')=='new generation'
    assert git(repo,'rev-parse','HEAD')==git(repo,'ls-remote','origin','refs/heads/main').split()[0]
    assert not output.exists()


def test_engine_render_uses_exact_original_loader_for_stage_and_final_source_verification():
    doc=yaml.safe_load((ROOT/'.github/workflows/engine-render.yml').read_text())
    steps=next(body['steps'] for body in doc['jobs'].values() if any(s.get('id')=='native_publication_stage' for s in body.get('steps',[])))
    byid={s['id']:s for s in steps if s.get('id')}
    stage=resolve_run_source(byid['native_publication_stage']['run'],ROOT)
    final=resolve_run_source(byid['native_publication']['run'],ROOT)
    assert 'engine_render_native_publish.sh' in byid['native_publication_stage']['run']
    assert stage.index('native_publication_capture_source')<stage.index('push_native_do')
    assert 'native_publication_prepare_source' in final and 'native_publication_source.sh' in final
    assert byid['native_publication']['env']['NATIVE_PUBLICATION_PUBLISHING_STEP']=='native_publication_stage'
