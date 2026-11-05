"""Multiple real local generations must survive native squash publication."""
import os
from pathlib import Path
import subprocess

import pytest
import yaml

ROOT=Path(__file__).resolve().parents[1]


def git(root,*args):
    return subprocess.run(['git','-C',str(root),*args],capture_output=True,check=True).stdout.decode().strip()


@pytest.mark.parametrize('prior_landed',[False,True])
def test_actual_metadata_preparation_conserves_prior_local_checkpoint_without_dirty_checkout_rebase(tmp_path,prior_landed):
    remote=tmp_path/'remote';remote.mkdir();git(remote,'init','-q','--bare')
    repo=tmp_path/'repo';repo.mkdir();git(repo,'init','-q','-b','main')
    git(repo,'config','user.name','fixture');git(repo,'config','user.email','fixture@example.invalid')
    (repo/'base').write_text('original source');git(repo,'add','.');git(repo,'commit','-qm','base')
    base=git(repo,'rev-parse','HEAD');git(repo,'remote','add','origin',str(remote));git(repo,'push','origin','main')
    (repo/'core-generation').write_text('core output');git(repo,'add','.');git(repo,'commit','-qm','earlier core checkpoint')
    core=git(repo,'rev-parse','HEAD')
    if prior_landed:
        squash=git(repo,'commit-tree',git(repo,'rev-parse','HEAD^{tree}'),'-p',base,'-m','actual prior squash')
        assert squash!=core;git(repo,'push','origin',squash+':main')
    (repo/'tail-generation').write_text('tail output');git(repo,'add','.');git(repo,'commit','-qm','final tail')
    head=git(repo,'rev-parse','HEAD');(repo/'dirty-later-data').write_text('must remain untouched')
    # Only the existing commodity page check and HTTP publication are test-owned
    # fakes. The ORIGINAL metadata replay and actual candidate Git tree execute.
    source=(ROOT/'scripts/ci/daily_engine_commit_outputs.sh').read_text()
    body=source.split('native_candidate=""\n',1)[1].split('while push_attempt; do',1)[0]
    body='native_candidate=""\n'+body
    shim=tmp_path/'bin';shim.mkdir();python=shim/'python3';python.write_text('#!/bin/sh\nexit 0\n');python.chmod(0o755)
    out=tmp_path/'outputs';candidate_file=tmp_path/'candidate'
    program='. "'+str(ROOT/'scripts/ci/push_retry.sh')+'"\n'
    program+='push_native_do() { printf "%s\\n" "$2" > "$CANDIDATE_FILE"; return 77; }\n'
    program+=body
    result=subprocess.run(['bash','-eo','pipefail','-c',program],cwd=repo,capture_output=True,text=True,
        env={**os.environ,'PATH':str(shim)+os.pathsep+os.environ['PATH'],'RUNNER_TEMP':str(tmp_path),
            'GITHUB_OUTPUT':str(out),'CANDIDATE_FILE':str(candidate_file),
            'NATIVE_PUBLICATION_PUBLISHING_STEP':'native_publication_stage','publisher_source_root':str(ROOT)})
    assert result.returncode==0,result.stderr
    candidate=candidate_file.read_text().strip().split(':')[0]
    assert git(repo,'rev-parse',candidate+'^')==git(repo,'ls-remote','origin','refs/heads/main').split()[0]
    assert git(repo,'show',candidate+':core-generation')=='core output'
    assert git(repo,'show',candidate+':tail-generation')=='tail output'
    assert git(repo,'rev-parse','HEAD')==head
    assert (repo/'dirty-later-data').read_text()=='must remain untouched'
    assert out.read_text()=='publication=pending\n'


def test_all_engine_publication_stages_upload_before_final_consumer_gate():
    steps=yaml.safe_load((ROOT/'.github/workflows/daily.yml').read_text())['jobs']['engine']['steps']
    byid={s['id']:s for s in steps if 'id' in s}
    for kind in ('leader','prophet','shadow','core','chronicle',''):
        stage='native_publication_'+(kind+'_' if kind else '')+'stage'
        origin=stage+'_origin';final={'leader':'leader_checkpoint','prophet':'prophet_checkpoint',
            'shadow':'prophet_stage_checkpoint'}.get(kind,'native_publication'+('_'+kind if kind else ''))
        a,b,c=(steps.index(byid[k]) for k in (stage,origin,final))
        assert b==a+1 and c==b+1
        assert byid[origin]['uses']=='actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02'
        assert byid[origin]['with']['if-no-files-found']=='error'
        assert byid[origin]['with']['overwrite'] is False
        assert stage+'.outcome' in byid[final]['if'] and origin+'.outcome' in byid[final]['if']
        assert byid[final]['env']['NATIVE_PUBLICATION_PUBLISHING_STEP']==stage
        assert 'native_checkpoint_settle.sh' in byid[final]['run']
    assert 'continue-on-error' not in byid['native_publication']
