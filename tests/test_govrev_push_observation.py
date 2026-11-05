from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import sys
import os
import pytest
import yaml

BASE = Path(__file__).resolve().parents[1]
HELPER = BASE / 'scripts/ci/govrev_candidate_proof.py'
spec = importlib.util.spec_from_file_location('push_proof', HELPER)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
spec2 = importlib.util.spec_from_file_location('gate_fixtures', BASE / 'tests/test_govrev_candidate_proof_gate.py')
gate = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(gate)

@pytest.mark.parametrize('code,body,expected', [
    (0,b'OK','successful'), (142,b'','effect_unknown'),
    (1,b'fatal: transport reset','effect_unknown'),
    (1,b'fatal: Authentication failed','effect_unknown'),
    (1,b'failed to lock ref','effect_unknown'),
    (1,b'! [rejected] HEAD -> main (fetch first)\n','definite_contention_rejection'),
    (1,b'! [rejected] HEAD -> main (non-fast-forward)\n','definite_contention_rejection'),
    (142,b'! [rejected] HEAD -> main (fetch first)\n','effect_unknown'),
    (1,b'! [rejected] HEAD -> main (fetch first)\n   HEAD -> main\n','effect_unknown'),
    (142,b'error: GH001: Large files detected','refused'),
    (1,b'error: GH006: Protected branch update failed','refused'),
    (1,b'error: GH013: Repository rule violations','refused'),
    (142,b'Permission denied','refused'),
    (142,b'error: GH001:' + b'x'*140000,'refused'),
])
def test_only_qualified_single_update_rejection_can_retry(code, body, expected):
    assert module._push_outcome(code, body) == expected


def cli(root, *args):
    return subprocess.run([sys.executable,str(HELPER),*args,'--root',str(root)],capture_output=True,text=True)


def prepared(tmp_path):
    root = gate._proof_tree(tmp_path)
    local = root / 'scripts/ci/govrev_candidate_proof.py'
    local.parent.mkdir(parents=True)
    local.write_bytes(HELPER.read_bytes())
    gate._git(root,'add','-A');gate._git(root,'commit','-qm','bind actual helper')
    remote = tmp_path / 'origin.git'
    subprocess.run(['git','init','--bare','-q',str(remote)],check=True)
    gate._git(root,'remote','add','origin',str(remote))
    gate._git(root,'push','-q','origin','HEAD:main')
    # The sealed generation has a new local commit the remote does not contain yet.
    (root/'README').write_text('new publication')
    gate._git(root,'add','-A');gate._git(root,'commit','-qm','new generation')
    assert gate._prove(root,tmp_path).returncode == 0
    identity=tmp_path/'push.identity.json'
    result=cli(root,'push-identity','--receipt',str(gate._receipt_path(tmp_path)),'--attempt','1','--out',str(identity))
    assert result.returncode==0,result.stdout+result.stderr
    return root,remote,identity


@pytest.mark.parametrize('state', ['landed','advanced','negative','unreadable','changed_origin','tampered_identity'])
def test_same_origin_observer_preserves_original_effect_and_unknown(tmp_path,state):
    root,remote,identity=prepared(tmp_path)
    expected=gate._git(root,'rev-parse','HEAD').strip()
    if state in ('landed','advanced'):
        gate._git(root,'push','-q','origin','HEAD:main')
    if state=='advanced':
        peer=tmp_path/'peer'
        subprocess.run(['git','clone','-q','-b','main',str(remote),str(peer)],check=True)
        gate._git(peer,'config','user.name','peer');gate._git(peer,'config','user.email','peer@test')
        (peer/'README').write_text('later main');gate._git(peer,'add','-A');gate._git(peer,'commit','-qm','later');gate._git(peer,'push','-q')
    elif state=='unreadable':
        remote.rename(tmp_path/'gone.git')
    elif state=='changed_origin':
        gate._git(root,'remote','set-url','origin',str(tmp_path/'different.git'))
    elif state=='tampered_identity':
        record=json.loads(identity.read_text());record['expected_commit']='0'*40;identity.write_text(json.dumps(record))
    out=tmp_path/'observation.json'
    result=cli(root,'observe-push','--identity',str(identity),'--out',str(out))
    assert result.returncode==(0 if state in ('landed','advanced') else 75),result.stderr
    record=json.loads(out.read_text())
    assert record['issuance_authority'] is False
    assert record['serving_generation_authority'] is False
    assert 'origin.git' not in out.read_text()
    if state in ('landed','advanced'):
        assert record['expected_commit']==expected
        assert record['current_ref_equals_expected']==(state=='landed')
    else:
        assert record['outcome']=='effect_unknown'


def wrapper():
    doc=yaml.safe_load((BASE/'.github/workflows/government-revenue-live.yml').read_text())
    body=next(s['run'] for s in doc['jobs']['refresh']['steps'] if s.get('name')=='stage reviewed source guards')
    return body[body.index('govrev_push_same_carrier()'):body.index('prepare_candidate_research_state()')]


@pytest.mark.parametrize('state', ['landed_timeout','unknown','refused','qledger_refused','contention'])
def test_wrapper_does_not_replay_unknown_or_refusal(tmp_path,state):
    root,remote,identity=prepared(tmp_path)
    # Identity is one per real attempt. Our preparatory API check must not be reused as a fresh push.
    identity.unlink()
    runtemp=tmp_path/'temp';runtemp.mkdir()
    proof=runtemp/'govrev-candidate-proof.receipt.json';proof.write_bytes(gate._receipt_path(tmp_path).read_bytes())
    if state=='landed_timeout':
        push="git push -q origin HEAD:main; return 142"
    elif state=='refused':
        push="printf '%s\\n' 'error: GH001: refused'; return 142"
    elif state=='qledger_refused':
        # Even if the commit is already remote, an explicit inherited control cannot observe-to-success.
        gate._git(root,'push','-q','origin','HEAD:main')
        push='PUSH_TERMINAL_RC=9; PUSH_FAIL_CLASS=qledger-integrity; return 9'
    elif state=='contention':
        push="printf '%s\\n' '! [rejected] HEAD -> main (fetch first)'; return 1"
    else:
        push="printf '%s\\n' 'fatal: transport reset'; return 142"
    script='set -euo pipefail\n'+f'. "{BASE / "scripts/ci/push_retry.sh"}"\n'+f'python() {{ {sys.executable} "$@"; }}\n'+wrapper()+f'\npush_do() {{ {push}; }}\n'+'''govrev_push_rc=0
govrev_push_same_carrier || govrev_push_rc=$?
if [ "$govrev_push_rc" -eq 0 ]; then
  printf '%s' "$GOVREV_PUSH_STATUS" > "$RUNNER_TEMP/success"
elif [ "$govrev_push_rc" -ne 1 ]; then
  exit "$govrev_push_rc"
else
  touch "$RUNNER_TEMP/retry_allowed"
fi
'''
    result=subprocess.run(['/bin/bash','-c',script],cwd=root,env={**os.environ,'RUNNER_TEMP':str(runtemp),'PUSH_ATTEMPT':'1'},capture_output=True,text=True)
    assert result.returncode=={'landed_timeout':0,'contention':0,'unknown':75,'refused':76,'qledger_refused':76}[state],result.stderr+result.stdout
    assert (runtemp/'retry_allowed').exists()==(state=='contention')
    assert (runtemp/'success').exists()==(state=='landed_timeout')
    assert not list(runtemp.glob('*.response.tmp'))
    if state in ('refused','qledger_refused'):
        assert not list(runtemp.glob('*.observation.json'))


def test_workflow_freezes_before_cleanup_and_preserves_budget_and_size():
    doc=yaml.safe_load((BASE/'.github/workflows/government-revenue-live.yml').read_text())
    commit=next(s['run'] for s in doc['jobs']['refresh']['steps'] if 'commit complete' in s.get('name',''))
    assert commit.index('elif [ "$govrev_push_rc" -ne 1 ]') < commit.index('push_abort_rebase')
    assert 'exit "$govrev_push_rc"' in commit
    assert 'PUSH_MAX_ATTEMPTS=2' in commit and 'PUSH_BUDGET_SECS=2700' in commit and 'GOVREV_REPROOFS=0' in commit
    assert len(commit)<=20563
    for step in doc['jobs']['refresh']['steps']:
        if 'run' in step:
            result=subprocess.run(['/bin/bash','-n'],input=step['run'],text=True,capture_output=True)
            assert result.returncode==0,result.stderr


@pytest.mark.parametrize('tampered', [False,True])
def test_reconciled_publication_witness_requires_same_proof_and_commit(tmp_path,tampered):
    root,remote,identity=prepared(tmp_path)
    gate._git(root,'push','-q','origin','HEAD:main')
    observation=tmp_path/'observation.json'
    assert cli(root,'observe-push','--identity',str(identity),'--out',str(observation)).returncode==0
    if tampered:
        record=json.loads(observation.read_text());record['proof_identity']='wrong';observation.write_text(json.dumps(record))
    out=tmp_path/'publication.json'
    result=cli(root,'publication-witness','--receipt',str(gate._receipt_path(tmp_path)),
        '--suite','tests/test_proof_gate_suite.py','--commit',gate._git(root,'rev-parse','HEAD').strip(),
        '--push-status','successful_after_same_carrier_observation','--push-observation',str(observation),'--out',str(out))
    assert result.returncode==(75 if tampered else 0),result.stderr+result.stdout
    if not tampered:
        record=json.loads(out.read_text())
        assert record['push_status_source']=='same_origin_original_commit_observation'
        assert record['push_observation_sha256']==hashlib.sha256(observation.read_bytes()).hexdigest()
        assert record['serving_generation_authority'] is False


def test_witness_binds_observation_to_the_same_original_identity(tmp_path):
    root,remote,identity=prepared(tmp_path)
    gate._git(root,'push','-q','origin','HEAD:main')
    observation=tmp_path/'observation.json'
    assert cli(root,'observe-push','--identity',str(identity),'--out',str(observation)).returncode==0
    commit=gate._git(root,'rev-parse','HEAD').strip()
    other=tmp_path/'other.identity.json'
    assert cli(root,'push-identity','--receipt',str(gate._receipt_path(tmp_path)),
        '--attempt','2','--out',str(other)).returncode==0
    out=tmp_path/'publication.json'
    common=('publication-witness','--receipt',str(gate._receipt_path(tmp_path)),
        '--suite','tests/test_proof_gate_suite.py','--commit',commit,
        '--push-status','successful_after_same_carrier_observation',
        '--push-observation',str(observation),'--out',str(out))
    mismatch=cli(root,*common,'--push-identity',str(other))
    assert mismatch.returncode==75,mismatch.stdout+mismatch.stderr
    assert not out.exists()
    result=cli(root,*common,'--push-identity',str(identity))
    assert result.returncode==0,result.stdout+result.stderr
    record=json.loads(out.read_text())
    assert record['push_status_source']=='same_origin_original_commit_observation'
    assert record['push_identity_sha256']==hashlib.sha256(identity.read_bytes()).hexdigest()
    assert record['observed_remote_commit']==commit


def landing_prepared(tmp_path):
    """prepared(), plus a sealed candidate commit that itself moves output bytes.

    The extra movement makes the sealed output projection distinguishable from
    the incumbent remote generation, so a ref without the landing cannot pass
    the projection walk.
    """
    root,remote,identity=prepared(tmp_path)
    queue=root/'data/government_revenue/candidate_queue.json'
    queue.write_text(json.dumps({'content_id':'grcq1-proofgate','counts':{'total':2}}))
    (root/'site/government-revenue-data/candidates.json').write_text(queue.read_text())
    gate._git(root,'add','-A');gate._git(root,'commit','-qm','sealed output movement')
    assert gate._prove(root,tmp_path).returncode==0
    sealed_identity=tmp_path/'landing.identity.json'
    result=cli(root,'push-identity','--receipt',str(gate._receipt_path(tmp_path)),
        '--attempt','1','--out',str(sealed_identity))
    assert result.returncode==0,result.stdout+result.stderr
    return root,remote,sealed_identity


def _peer_advance(tmp_path,root,remote,*,different_generation=False):
    peer=tmp_path/'peer'
    subprocess.run(['git','clone','-q','-b','main',str(remote),str(peer)],check=True)
    gate._git(peer,'config','user.name','peer');gate._git(peer,'config','user.email','peer@test')
    if different_generation:
        payload='{"content_id":"grcq1-peer-generation"}'
        (peer/'data/government_revenue/candidate_queue.json').write_text(payload)
        (peer/'site/government-revenue-data/candidates.json').write_text(payload)
    else:
        (peer/'README').write_text('later unrelated movement')
    gate._git(peer,'add','-A');gate._git(peer,'commit','-qm','peer advance');gate._git(peer,'push','-q')
    return gate._git(peer,'rev-parse','HEAD').strip()


def _push_squash_landing(root,remote,parent,*,message='squash landing',
                         source_overrides=(),output_overrides=(),removals=(),additions=(),mode_overrides=()):
    """Compose and push a real squash landing: the sealed candidate tree
    re-parented onto the remote tip.  The landing commit never descends from
    the candidate, and the local checkout never moves."""
    env={**os.environ,'GIT_INDEX_FILE':str(root/'.git'/'govrev-squash-index')}

    def run(*args,stdin=None):
        return subprocess.run(['git','-C',str(root),*args],input=stdin,capture_output=True,
            text=True,env=env,check=True).stdout

    candidate_tree=gate._git(root,'rev-parse','HEAD^{tree}').strip()
    run('read-tree',candidate_tree)
    for path,body in source_overrides:
        oid=run('hash-object','-w','--stdin',stdin=body).strip()
        run('update-index','--add','--cacheinfo',f'100644,{oid},{path}')
    for path,body in output_overrides:
        oid=run('hash-object','-w','--stdin',stdin=body).strip()
        run('update-index','--add','--cacheinfo',f'100644,{oid},{path}')
    for path in removals:
        run('update-index','--force-remove',path)
    for path,body in additions:
        oid=run('hash-object','-w','--stdin',stdin=body).strip()
        run('update-index','--add','--cacheinfo',f'100644,{oid},{path}')
    for mode,path in mode_overrides:
        oid=run('ls-tree','HEAD','--',path).strip().split()[2]
        run('update-index','--cacheinfo',f'{mode},{oid},{path}')
    tree=run('write-tree').strip()
    squash=run('commit-tree',tree,'-p',parent,'-m',message).strip()
    gate._git(root,'push','-q',remote,f'{squash}:refs/heads/main')
    return squash


def witness_cli(root,tmp_path,identity,*extra,status='successful'):
    out=tmp_path/'publication.json'
    result=cli(root,'publication-witness','--receipt',str(gate._receipt_path(tmp_path)),
        '--suite','tests/test_proof_gate_suite.py','--commit',gate._git(root,'rev-parse','HEAD').strip(),
        '--push-status',status,'--push-identity',str(identity),*extra,'--out',str(out))
    return result,out


@pytest.mark.parametrize('state', [
    'exact', 'later_unrelated_movement', 'squash', 'not_landed', 'unreadable',
    'changed_origin', 'tampered_identity', 'newer_differing_generation',
    'squash_changed_source', 'squash_changed_output', 'squash_added_output',
    'squash_deleted_output', 'squash_mode_change', 'squash_symlink_output',
    'squash_then_newer_output', 'squash_quoted_source',
])
def test_publication_witness_records_only_the_actually_landed_generation(tmp_path,state):
    root,remote,identity=landing_prepared(tmp_path)
    candidate=gate._git(root,'rev-parse','HEAD').strip()
    expected={'exact':0,'later_unrelated_movement':0,'squash':0}
    if state=='exact':
        gate._git(root,'push','-q','origin','HEAD:main')
    elif state=='later_unrelated_movement':
        gate._git(root,'push','-q','origin','HEAD:main')
        moved=_peer_advance(tmp_path,root,remote)
    elif state=='squash':
        parent=gate._git(root,'ls-remote',remote,'refs/heads/main').split()[0]
        moved=_push_squash_landing(root,remote,parent)
    elif state=='squash_then_newer_output':
        parent=gate._git(root,'ls-remote',remote,'refs/heads/main').split()[0]
        _push_squash_landing(root,remote,parent)
        moved=_peer_advance(tmp_path,root,remote,different_generation=True)
    elif state=='squash_quoted_source':
        parent=gate._git(root,'ls-remote',remote,'refs/heads/main').split()[0]
        moved=_push_squash_landing(root,remote,parent,source_overrides=(
            ('scripts/é-source.py','changed protected source\n'),))
    elif state=='newer_differing_generation':
        moved=_peer_advance(tmp_path,root,remote,different_generation=True)
    elif state=='squash_changed_source':
        parent=gate._git(root,'ls-remote',remote,'refs/heads/main').split()[0]
        moved=_push_squash_landing(root,remote,parent,source_overrides=(
            ('tests/test_proof_gate_suite.py','def test_tampered():\n    assert False\n'),))
    elif state=='squash_changed_output':
        parent=gate._git(root,'ls-remote',remote,'refs/heads/main').split()[0]
        moved=_push_squash_landing(root,remote,parent,output_overrides=(
            ('data/government_revenue/candidate_queue.json','{"content_id":"grcq1-rewritten"}'),))
    elif state=='squash_added_output':
        parent=gate._git(root,'ls-remote',remote,'refs/heads/main').split()[0]
        moved=_push_squash_landing(root,remote,parent,additions=(
            ('data/government_revenue/extra.json','{}'),))
    elif state=='squash_deleted_output':
        parent=gate._git(root,'ls-remote',remote,'refs/heads/main').split()[0]
        moved=_push_squash_landing(root,remote,parent,removals=(
            'site/government-revenue-data/candidates.json',))
    elif state in ('squash_mode_change','squash_symlink_output'):
        parent=gate._git(root,'ls-remote',remote,'refs/heads/main').split()[0]
        moved=_push_squash_landing(root,remote,parent,mode_overrides=(
            ('100755' if state=='squash_mode_change' else '120000',
             'data/government_revenue/candidate_queue.json'),))
    elif state=='changed_origin':
        other=tmp_path/'different.git'
        subprocess.run(['git','init','--bare','-q',str(other)],check=True)
        gate._git(root,'remote','set-url','origin',str(other))
    elif state=='tampered_identity':
        record=json.loads(identity.read_text());record['expected_commit']='0'*40
        identity.write_text(json.dumps(record))
    elif state=='unreadable':
        remote.rename(tmp_path/'gone.git')
    result,out=witness_cli(root,tmp_path,identity)
    assert result.returncode==expected.get(state,75),result.stdout+result.stderr
    if state not in expected:
        assert not out.exists()
        assert 'origin.git' not in (result.stdout+result.stderr)
        return
    witness=json.loads(out.read_text())
    assert witness['issuance_authority'] is False
    assert witness['serving_generation_authority'] is False
    assert witness['committed_generation']['commit']==candidate
    assert 'origin.git' not in out.read_text()
    if state=='exact':
        assert witness['observed_remote_commit']==candidate
        assert witness['landing_commit']==candidate
        assert witness['landing']=='fast_forward'
        assert witness['push_status_source']=='same_origin_original_push_identity_readback'
        assert witness['push_identity_sha256']==hashlib.sha256(identity.read_bytes()).hexdigest()
    elif state=='later_unrelated_movement':
        # The recorded remote commit is the observed main SHA, not the candidate.
        assert witness['observed_remote_commit']==moved
        assert witness['observed_remote_commit']!=candidate
        assert witness['landing_commit']==candidate
        assert witness['landing']=='fast_forward'
    elif state=='squash':
        # A real squash landing differs from the candidate and does not descend
        # from it; the same sealed projection/source qualifies, and the actual
        # remote SHA is recorded while the candidate stays in committed_generation.
        assert witness['observed_remote_commit']==moved
        assert witness['observed_remote_commit']!=candidate
        assert witness['landing_commit']==moved
        assert witness['landing']=='squash_projection'
        assert witness['committed_generation']['commit']==candidate


def test_publication_witness_refuses_without_original_push_identity(tmp_path):
    root,remote,identity=landing_prepared(tmp_path)
    gate._git(root,'push','-q','origin','HEAD:main')
    # Drop the identity argument: the bare success status is not landing evidence,
    # even though the sealed generation really is sitting on the remote.
    out=tmp_path/'publication-no-identity.json'
    result=cli(root,'publication-witness','--receipt',str(gate._receipt_path(tmp_path)),
        '--suite','tests/test_proof_gate_suite.py','--commit',gate._git(root,'rev-parse','HEAD').strip(),
        '--push-status','successful','--out',str(out))
    assert result.returncode==75,result.stdout+result.stderr
    assert not out.exists()
    assert 'landing evidence' in (result.stdout+result.stderr)
    # And the exact same invocation with the original identity qualifies.
    witness,out_ok=witness_cli(root,tmp_path,identity)
    assert witness.returncode==0,witness.stdout+witness.stderr
    assert json.loads(out_ok.read_text())['observed_remote_commit']==gate._git(root,'rev-parse','HEAD').strip()


def test_publication_witness_atomic_race_preserves_existing_original(tmp_path,monkeypatch):
    root,remote,identity=landing_prepared(tmp_path)
    gate._git(root,'push','-q','origin','HEAD:main')
    out=tmp_path/'publication.json'
    real=module._landing_generation
    def racing(*args):
        result=real(*args)
        out.write_bytes(b'original winner must survive\n')
        return result
    monkeypatch.setattr(module,'_landing_generation',racing)
    args=module.build_parser().parse_args(['publication-witness','--root',str(root),
        '--receipt',str(gate._receipt_path(tmp_path)),'--suite','tests/test_proof_gate_suite.py',
        '--commit',gate._git(root,'rev-parse','HEAD').strip(),'--push-status','successful',
        '--push-identity',str(identity),'--out',str(out)])
    assert module.command_publication_witness(args)!=0
    assert out.read_bytes()==b'original winner must survive\n'


def test_workflow_wires_the_original_push_identity_into_the_witness():
    body=wrapper()
    assert 'GOVREV_PUSH_IDENTITY="$prefix.identity.json"' in body
    assert '"$prefix.identity.json"' in body and '--attempt "$PUSH_ATTEMPT"' in body
    doc=yaml.safe_load((BASE/'.github/workflows/government-revenue-live.yml').read_text())
    commit=next(s['run'] for s in doc['jobs']['refresh']['steps'] if 'commit complete' in s.get('name',''))
    assert '--push-identity "$GOVREV_PUSH_IDENTITY"' in commit
    assert commit.index('publication-witness')<commit.index('--push-identity "$GOVREV_PUSH_IDENTITY"')<commit.index('--out "$RUNNER_TEMP/govrev-candidate-proof.publication.json"')
    assert len(commit)<=20563


def test_interrupted_push_raw_response_is_outside_retained_artifact_namespace(tmp_path):
    root, remote, identity = prepared(tmp_path)
    runtemp = tmp_path / "temp"
    runtemp.mkdir()
    (runtemp / "govrev-candidate-proof.receipt.json").write_bytes(gate._receipt_path(tmp_path).read_bytes())
    script = "set -euo pipefail\n" + f'. "{BASE / "scripts/ci/push_retry.sh"}"\n' + f'python() {{ {sys.executable} "$@"; }}\n' + wrapper() + '''
push_do() { printf '%s' 'synthetic-credential-url'; exit 97; }
govrev_push_same_carrier
'''
    result = subprocess.run(["/bin/bash", "-c", script], cwd=root,
        env={**os.environ, "RUNNER_TEMP": str(runtemp), "PUSH_ATTEMPT": "1"}, capture_output=True, text=True)
    assert result.returncode == 97
    private = list(runtemp.glob("govrev-private-push-response.*"))
    assert len(private) == 1
    assert private[0].stat().st_mode & 0o777 == 0o600
    assert private[0].read_text() == "synthetic-credential-url"
    retained = list(runtemp.glob("govrev-candidate-proof*"))
    assert private[0] not in retained
    assert all("synthetic-credential-url" not in path.read_text() for path in retained)


@pytest.mark.parametrize("checkout", ["main", "dispatch_branch", "detached", "unreadable"])
def test_wrapper_checks_actual_main_before_any_push_effect(tmp_path, checkout):
    root = tmp_path / "checkout"
    root.mkdir()
    if checkout != "unreadable":
        gate._git(root, "init", "-q", "-b", "main")
        gate._git(root, "config", "user.name", "guard test")
        gate._git(root, "config", "user.email", "guard@test")
        (root / "seed").write_text("seed")
        gate._git(root, "add", "seed")
        gate._git(root, "commit", "-qm", "seed")
        if checkout == "dispatch_branch":
            gate._git(root, "checkout", "-qb", "feature/dispatch")
        elif checkout == "detached":
            gate._git(root, "checkout", "-q", "--detach", "HEAD")
    runtemp = tmp_path / "temp"
    runtemp.mkdir()
    script = "set -euo pipefail\n" + f'. "{BASE / "scripts/ci/push_retry.sh"}"\n' + wrapper() + '''
python() { printf '%s\n' "$*" >> "$RUNNER_TEMP/python-called"; }
push_do() { touch "$RUNNER_TEMP/push-called"; }
govrev_push_same_carrier
'''
    result = subprocess.run(["/bin/bash", "-c", script], cwd=root,
        env={**os.environ, "RUNNER_TEMP": str(runtemp), "PUSH_ATTEMPT": "1",
             "PUSH_MAIN_BRANCHES": "main", "GIT_CEILING_DIRECTORIES": str(tmp_path)},
        capture_output=True, text=True)
    allowed = checkout == "main"
    assert result.returncode == (0 if allowed else 76), result.stdout + result.stderr
    assert (runtemp / "python-called").exists() is allowed
    assert (runtemp / "push-called").exists() is allowed
    if not allowed:
        assert not list(runtemp.glob("govrev-candidate-proof*"))
        assert not list(runtemp.glob("govrev-private-push-response.*"))
