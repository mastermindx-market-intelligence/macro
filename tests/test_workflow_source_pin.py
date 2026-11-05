"""Original workflow shell bytes survive a prior publisher's real rebase."""
import os
from pathlib import Path
import subprocess

import pytest

from scripts.workflow_run_source import (
    WorkflowRunSourceError,pinned_workflow_shell,resolve_run_source,resolved_workflow_text,
)


def git(root,*args):
    return subprocess.run(['git','-C',str(root),*args],capture_output=True,text=True,check=True).stdout.strip()


def test_original_shell_executes_original_object_after_real_checkout_drift(tmp_path):
    root=tmp_path/'source';root.mkdir();git(root,'init','-q','-b','main')
    git(root,'config','user.name','fixture');git(root,'config','user.email','fixture@example.invalid')
    path='scripts/ci/original.sh';script=root/path;script.parent.mkdir(parents=True)
    script.write_text('# EXTRACTED-VERBATIM-FROM: .github/workflows/daily.yml\necho ORIGINAL_SHELL\n')
    git(root,'add','.');git(root,'commit','-qm','original');original=git(root,'rev-parse','HEAD')
    git(root,'checkout','-qb','new-main');script.write_text('echo MUTATED_SHELL\n')
    git(root,'add','.');git(root,'commit','-qm','changed publisher')
    git(root,'checkout','-qb','producer',original);(root/'generation').write_text('original')
    git(root,'add','.');git(root,'commit','-qm','original generation');git(root,'rebase','new-main')
    runner=tmp_path/'runner';runner.mkdir();body=pinned_workflow_shell(path,'native_publication_second_stage')
    env={**os.environ,'GITHUB_WORKFLOW_SHA':original,'GITHUB_SHA':original,'RUNNER_TEMP':str(runner),
         'GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'1','GITHUB_JOB':'engine'}
    result=subprocess.run(['bash','-eo','pipefail','-c',body],cwd=root,env=env,capture_output=True,text=True)
    assert result.returncode==0 and result.stdout=='ORIGINAL_SHELL\n',result.stderr
    # Same original step cannot replay its executable/publishing effect.
    duplicate=subprocess.run(['bash','-eo','pipefail','-c',body],cwd=root,env=env,capture_output=True,text=True)
    assert duplicate.returncode!=0 and 'ORIGINAL_SHELL' not in duplicate.stdout


@pytest.mark.parametrize('change',['prefix','suffix','missing-marker','changed-object'])
def test_source_resolution_cannot_hide_extra_commands_or_changed_loader(tmp_path,change):
    path='scripts/ci/original.sh';script=tmp_path/path;script.parent.mkdir(parents=True)
    script.write_text('# EXTRACTED-VERBATIM-FROM: .github/workflows/daily.yml\npython -m scripts.actual_guard\n')
    body=pinned_workflow_shell(path,'native_publication_stage')
    if change=='prefix':body='echo hidden\n'+body
    elif change=='suffix':body+='echo hidden\n'
    elif change=='missing-marker':body='\n'.join(body.splitlines()[1:])
    else:body=body.replace('$GITHUB_WORKFLOW_SHA:', 'HEAD:')
    with pytest.raises(WorkflowRunSourceError):resolve_run_source(body,tmp_path)


def test_existing_source_guards_see_pinned_shell_at_its_original_position(tmp_path):
    path='scripts/ci/original.sh';script=tmp_path/path;script.parent.mkdir(parents=True)
    script.write_text('# EXTRACTED-VERBATIM-FROM: .github/workflows/daily.yml\npython -m scripts.original_business\n')
    body=pinned_workflow_shell(path,'native_publication_stage')
    assert resolve_run_source(body,tmp_path)==script.read_text()
    workflow=tmp_path/'workflow.yml'
    workflow.write_text('before\n    run: |\n'+''.join('      '+line+'\n' for line in body.splitlines())+'after\n')
    resolved=resolved_workflow_text(workflow,tmp_path)
    assert resolved.index('before')<resolved.index('scripts.original_business')<resolved.index('after')
    assert 'native-publication-shell-' not in resolved


def test_original_shell_refuses_symlink_git_object_before_execution(tmp_path):
    root=tmp_path/'source';root.mkdir();git(root,'init','-q');git(root,'config','user.name','fixture')
    git(root,'config','user.email','fixture@example.invalid');script=root/'scripts/ci/original.sh'
    script.parent.mkdir(parents=True);script.symlink_to('/not-an-executable-authority')
    git(root,'add','.');git(root,'commit','-qm','symlink');original=git(root,'rev-parse','HEAD')
    runner=tmp_path/'runner';runner.mkdir()
    result=subprocess.run(['bash','-eo','pipefail','-c',pinned_workflow_shell('scripts/ci/original.sh','stage')],
        cwd=root,env={**os.environ,'GITHUB_WORKFLOW_SHA':original,'GITHUB_SHA':original,
            'RUNNER_TEMP':str(runner),'GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'1','GITHUB_JOB':'engine'},
        capture_output=True,text=True)
    assert result.returncode==76 and not list(runner.iterdir())
