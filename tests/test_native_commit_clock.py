"""Real future Git mint; provider JSON reconstruction is offline, not CI proof."""
from datetime import datetime,timezone
import hashlib
import os
from pathlib import Path
import re
import subprocess
import pytest
import yaml
from scripts.ci import native_commit_clock as clock

ROOT=Path(__file__).resolve().parents[1]
def git(root,*args):return subprocess.run(['git','-C',str(root),*args],check=True,capture_output=True).stdout

@pytest.mark.parametrize('explicit',[False,True])
def test_real_future_mint_under_non_utc_process_preserves_intended_epochs_and_api_object_hash(tmp_path,monkeypatch,explicit):
    git(tmp_path,'init','-q','-b','main');git(tmp_path,'config','user.name','Original Author');git(tmp_path,'config','user.email','original@example.invalid')
    monkeypatch.setenv('TZ','America/Vancouver')
    (tmp_path/'output').write_text('original generation');git(tmp_path,'add','.');git(tmp_path,'commit','-qm','original source')
    parent=git(tmp_path,'rev-parse','HEAD').decode().strip()
    (tmp_path/'output').write_text('next exact generation');git(tmp_path,'add','.');tree=git(tmp_path,'write-tree').decode().strip()
    monkeypatch.setattr(clock.time,'time',lambda:1793904000.0)
    author=committer=1793904000
    if explicit:
        a='2026-11-05T11:23:34-08:00';c='2026-11-05T21:45:56+09:00'
        monkeypatch.setenv('GIT_AUTHOR_DATE',a);monkeypatch.setenv('GIT_COMMITTER_DATE',c)
        author=int(datetime.fromisoformat(a).timestamp());committer=int(datetime.fromisoformat(c).timestamp())
    else:
        monkeypatch.delenv('GIT_AUTHOR_DATE',raising=False);monkeypatch.delenv('GIT_COMMITTER_DATE',raising=False)
    assert clock.commit(tmp_path,['-m','one original mint — exact message'])==0
    head=git(tmp_path,'rev-parse','HEAD').decode().strip();raw=git(tmp_path,'cat-file','commit',head)
    assert git(tmp_path,'rev-parse','HEAD^').decode().strip()==parent
    assert git(tmp_path,'rev-parse','HEAD^{tree}').decode().strip()==tree
    assert re.search(rb'^author Original Author <original@example.invalid> '+str(author).encode()+rb' \+0000$',raw,re.M)
    assert re.search(rb'^committer Original Author <original@example.invalid> '+str(committer).encode()+rb' \+0000$',raw,re.M)
    # Exact supported unsigned Git REST representation. The CORE consumer still
    # independently authenticates/materializes these objects under its own cap.
    def identity(when):return {'name':'Original Author','email':'original@example.invalid','date':datetime.fromtimestamp(when,timezone.utc).isoformat().replace('+00:00','Z')}
    api={'tree':{'sha':tree},'parents':[{'sha':parent}],'author':identity(author),'committer':identity(committer),'message':'one original mint — exact message'}
    def header(role):
        row=api[role];epoch=int(datetime.fromisoformat(row['date'].replace('Z','+00:00')).timestamp())
        return role+' '+row['name']+' <'+row['email']+'> '+str(epoch)+' +0000'
    reconstructed=('tree '+api['tree']['sha']+'\n'+''.join('parent '+p['sha']+'\n' for p in api['parents'])+header('author')+'\n'+header('committer')+'\n\n'+api['message']+'\n').encode()
    assert reconstructed==raw
    assert hashlib.sha1(b'commit '+str(len(reconstructed)).encode()+b'\0'+reconstructed).hexdigest()==head
    assert os.environ['TZ']=='America/Vancouver'
    if explicit:assert os.environ['GIT_AUTHOR_DATE']==a and os.environ['GIT_COMMITTER_DATE']==c


def test_malformed_explicit_identity_is_refused_before_candidate_mint(tmp_path,monkeypatch):
    git(tmp_path,'init','-q');git(tmp_path,'config','user.name','fixture');git(tmp_path,'config','user.email','fixture@example.invalid')
    (tmp_path/'output').write_text('original');git(tmp_path,'add','.');git(tmp_path,'commit','-qm','original');head=git(tmp_path,'rev-parse','HEAD')
    (tmp_path/'output').write_text('pending');git(tmp_path,'add','.')
    monkeypatch.setenv('GIT_AUTHOR_DATE','invalid original date')
    with pytest.raises(ValueError,match='original_git_identity_date_unqualified'):clock.commit(tmp_path,['-m','must not mint'])
    assert git(tmp_path,'rev-parse','HEAD')==head and git(tmp_path,'diff','--cached','--name-only').strip()==b'output'


def test_only_four_actual_original_candidate_boundaries_select_canonical_mint():
    for name in ('leader','prophet','stage'):
        body=(ROOT/f'scripts/ci/daily_engine_{name}_checkpoint.sh').read_text()
        assert body.count('push_native_commit -m ')==1 and '\ngit commit -m ' not in body
        assert body.index('native_publication_prepare_source')<body.index('push_native_commit -m ')<body.index('push_native_do')
    doc=yaml.safe_load((ROOT/'.github/workflows/fms-acquire.yml').read_text())
    stage=next(s for s in doc['jobs']['acquire']['steps'] if s.get('id')=='native_publication_stage')['run']
    assert stage.index('native_publication_capture_source')<stage.index('-m scripts.ci.native_commit_clock')<stage.index('native_args=(--native-deadline')<stage.index('-m scripts.ci.fms_persist')
    assert 'git commit -m "fms-acquire:' in stage,'non-native route keeps its existing mint'
    assert 'scripts/ci/native_commit_clock.py' in (ROOT/'scripts/ci/native_publication_source.sh').read_text()
