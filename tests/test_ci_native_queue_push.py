"""Canonical supplier tests; no old private artifact is an input."""
import copy
import json
from pathlib import Path
import subprocess
import os

import pytest
import yaml

from scripts.ci import native_queue_push as m
from scripts.ci.native_publication import ABSENT
from scripts.ci.native_publication_origin import decode_origin


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], capture_output=True,
                          text=True, check=True).stdout.strip()


@pytest.fixture
def candidate(tmp_path, monkeypatch):
    root = tmp_path / 'source'
    root.mkdir()
    git(root, 'init', '-q')
    git(root, 'config', 'user.name', 'fixture')
    git(root, 'config', 'user.email', 'fixture@example.invalid')
    (root / 'artifact.json').write_text('old generation')
    (root / 'old').write_text('delete this')
    git(root, 'add', '.')
    git(root, 'commit', '-qm', 'base')
    base = git(root, 'rev-parse', 'HEAD')
    (root / 'artifact.json').write_text('sealed generation')
    (root / 'old').unlink()
    (root / 'a').write_text('single character path')
    git(root, 'add', '-A')
    git(root, 'commit', '-qm', 'one generated generation')
    head = git(root, 'rev-parse', 'HEAD')
    runtemp = tmp_path / 'runner'
    runtemp.mkdir()
    environment = {'GITHUB_REPOSITORY': m.REPOSITORY, 'GITHUB_REF': 'refs/heads/main',
        'GITHUB_JOB': 'shock', 'NATIVE_PUBLICATION_TOKEN_ORIGIN': 'GITHUB_TOKEN', 'NATIVE_PUBLICATION_PUBLISHING_STEP': 'native_publication_stage',
        'GITHUB_WORKFLOW_REF': m.REPOSITORY + '/.github/workflows/commodity-sentinel.yml@refs/heads/main',
        'GITHUB_WORKFLOW_SHA': base, 'GITHUB_RUN_ID': '42000000000', 'GITHUB_RUN_ATTEMPT': '1',
        'RUNNER_TEMP': str(runtemp), 'GITHUB_OUTPUT': str(tmp_path / 'outputs')}
    for key, value in environment.items():
        monkeypatch.setenv(key, value)
    return root, head, environment


def pull(head, marker):
    repository = {'id': 1, 'full_name': m.REPOSITORY}
    return {'number': 7, 'head': {'sha': head, 'repo': repository},
        'base': {'ref': 'main', 'repo': repository}, 'state': 'open', 'draft': False,
        'merged': False, 'labels': [{'name': m.LABEL}], 'body': marker,
        'user': {'id': 41898282, 'login': 'github-actions[bot]'}}


class ExistingIntent:
    def __init__(self, candidate, mutation=None):
        self.root, self.head, self.env = candidate
        outputs = m.projection(self.root, self.head)
        locator, _, _ = m.producer_identity(self.head, m.projection_digest(outputs))
        self.pull = pull(self.head, m.intent_pointer(os.environ['NATIVE_PUBLICATION_TOKEN_ORIGIN'],locator))
        self.events = []
        self.mutation = mutation

    def request(self, method, path, body=None):
        self.events.append((method, path))
        if method == 'POST':
            assert path == '/issues/7/labels' and body == {'labels': [m.LABEL]}
            # Namespace admission may exist; uploadable origin must NOT exist.
            assert not list(Path(self.env['RUNNER_TEMP']).rglob('ci-proof-admission.json'))
            return [{'name': m.LABEL}]
        if path.startswith('/pulls?'):
            return [copy.deepcopy(self.pull)]
        if path == '/pulls/7':
            result = copy.deepcopy(self.pull)
            if self.mutation:
                self.mutation(result)
            return result
        if path == '/git/commits/' + self.head:
            return {'sha': self.head, 'tree': {'sha': git(self.root, 'rev-parse', 'HEAD^{tree}')}}
        raise AssertionError((method, path))


def test_real_git_projection_preserves_mode_blob_and_confirmed_deletion(candidate):
    root, head, _ = candidate
    outputs = {x.path: x for x in m.projection(root, head)}
    assert set(outputs) == {'a', 'artifact.json', 'old'}
    assert outputs['old'].mode is ABSENT and outputs['old'].blob_sha is ABSENT
    assert outputs['a'].mode == '100644'
    assert outputs['a'].blob_sha == git(root, 'rev-parse', head + ':a')


def test_existing_label_requires_explicit_original_request_and_readback_before_origin(candidate):
    api = ExistingIntent(candidate)
    root, head, env = candidate
    path = m.stage(api, root, 'main', head, 1)
    assert api.events[1:3] == [('POST', '/issues/7/labels'), ('GET', '/pulls/7')]
    envelope = decode_origin(path.read_bytes(), repository_id=1, repository_full_name=m.REPOSITORY)
    origin = envelope['producer_origin']
    assert origin['published_source_head'] == head
    assert origin['publishing_step'] == 'native_publication_stage'
    outputs = dict(line.split('=', 1) for line in Path(env['GITHUB_OUTPUT']).read_text().splitlines())
    assert outputs['native_origin_path'] == str(path)
    assert outputs['native_origin_name'].endswith('-native_publication_stage-' + origin['original_generation'])


@pytest.mark.parametrize('mutation', [
    lambda p: p['head'].update(sha='f' * 40),
    lambda p: p['base'].update(ref='codex/merge-queue-pilot'),
    lambda p: p.update(labels=[]),
    lambda p: p.update(state='closed'),
    lambda p: p['user'].update(id=2),
])
def test_changed_or_unconfirmed_label_subject_never_exports_origin(candidate, mutation):
    api = ExistingIntent(candidate, mutation)
    root, head, env = candidate
    with pytest.raises(m.PublicationHeld):
        m.stage(api, root, 'main', head, 1)
    assert not list(Path(env['RUNNER_TEMP']).rglob('ci-proof-admission.json'))
    assert not Path(env['GITHUB_OUTPUT']).exists()


def test_original_stage_namespace_blocks_second_effect(candidate):
    api = ExistingIntent(candidate)
    root, head, _ = candidate
    m.stage(api, root, 'main', head, 1)
    events = list(api.events)
    with pytest.raises(FileExistsError):
        m.stage(api, root, 'main', head, 1)
    assert api.events == events


def test_changed_attempt_does_not_adopt_existing_intent(candidate, monkeypatch):
    api = ExistingIntent(candidate)
    root, head, env = candidate
    monkeypatch.setenv('GITHUB_RUN_ATTEMPT', '2')
    with pytest.raises(m.PublicationHeld, match='another_original'):
        m.stage(api, root, 'main', head, 1)
    assert not any(method == 'POST' for method, _ in api.events)
    assert not list(Path(env['RUNNER_TEMP']).rglob('ci-proof-admission.json'))


def test_unqualified_producer_is_not_generic_origin(candidate, monkeypatch):
    api = ExistingIntent(candidate)
    root, head, _ = candidate
    monkeypatch.setenv('GITHUB_JOB', 'refresh')
    with pytest.raises(m.PublicationHeld, match='not_allowlisted'):
        m.stage(api, root, 'main', head, 1)
    assert api.events == []


@pytest.mark.parametrize('method,path', [
    ('PUT', '/pulls/7/merge'), ('POST', '/graphql'), ('PUT', '/pulls/7/update-branch'),
    ('POST', '/pulls/7/merge'), ('DELETE', '/issues/7/labels/hold'),
])
def test_forbidden_effects_are_structurally_unreachable(method, path):
    api = object.__new__(m.GitHub)
    with pytest.raises(m.PublicationHeld, match='endpoint_not_admitted'):
        api.request(method, path)


def test_complete_effective_rules_required_and_absence_only_is_off(candidate):
    root, _, _ = candidate
    class Read:
        def request(self, method, path):
            assert method == 'GET'
            return []
    assert m.protection(Read(), root, 1, 'main') is None
    class Denied:
        def request(self, *args):
            raise m.PublicationHeld('credential_refused')
    with pytest.raises(m.PublicationHeld):
        m.protection(Denied(), root, 1, 'main')
    class Incomplete:
        def request(self, *args):
            return {'rules': []}
    with pytest.raises(m.PublicationHeld):
        m.protection(Incomplete(), root, 1, 'main')


@pytest.mark.parametrize('invalid', [None, 'truncated', 'wrong-mode'])
def test_requested_tree_paths_are_complete_without_reading_unrelated_subtrees(invalid):
    commit, root_tree, child_tree, unrelated = ['a' * 40, 'b' * 40, 'c' * 40, 'd' * 40]
    class Metadata:
        def __init__(self): self.paths = []
        def request(self, method, path):
            assert method == 'GET'
            self.paths.append(path)
            if path == '/git/commits/' + commit:
                return {'sha': commit, 'tree': {'sha': root_tree}}
            if path == '/git/trees/' + root_tree:
                return {'sha': root_tree, 'truncated': invalid == 'truncated', 'tree': [
                    {'path': 'selected', 'type': 'tree', 'mode': '100644' if invalid == 'wrong-mode' else '040000', 'sha': child_tree},
                    {'path': 'unrelated-large-data', 'type': 'tree', 'mode': '040000', 'sha': unrelated}]}
            if path == '/git/trees/' + child_tree:
                return {'sha': child_tree, 'truncated': False, 'tree': [
                    {'path': 'present', 'type': 'blob', 'mode': '100644', 'sha': 'e' * 40}]}
            raise AssertionError('unrelated subtree/blob payload must not be read: ' + path)
    api = Metadata()
    if invalid:
        with pytest.raises(m.PublicationHeld):
            m.tree(api, commit, ['selected/present', 'selected/deleted'])
    else:
        found, identity = m.tree(api, commit, ['selected/present', 'selected/deleted'])
        assert identity == root_tree and set(found) == {'selected/present'}
        assert '/git/trees/' + unrelated not in api.paths


def test_nonmain_forced_and_deleted_routes_retain_legacy_behavior(candidate):
    root, _, _ = candidate
    assert m.destination(root, ['--force', 'origin', 'HEAD:live-data']) is None
    assert m.destination(root, ['origin', '--delete', 'machine-output']) is None
    with pytest.raises(m.PublicationHeld):
        m.destination(root, ['--force', 'origin', 'HEAD:main'])


def test_local_non_github_origin_never_acquires_api_or_native_authority(candidate, tmp_path, monkeypatch):
    root, _, _ = candidate
    git(root, 'remote', 'add', 'origin', str(tmp_path / 'local.git'))
    monkeypatch.setattr(m, 'GitHub', lambda *args: pytest.fail('unexpected API authority'))
    assert m.main(['publish', '--root', str(root), '--push-arg=origin', '--push-arg=HEAD:main']) == m.LEGACY


@pytest.mark.parametrize('state', ['published', 'pending', 'superseded', 'missing',
                                  'truncated', 'wrong_head', 'wrong_ancestry'])
@pytest.mark.parametrize('credential',['GITHUB_TOKEN','ADMIN_GH_TOKEN'])
def test_readonly_settlement_requires_original_protected_landing_and_projection(candidate, monkeypatch, state,credential):
    root, head, _ = candidate
    if credential=='ADMIN_GH_TOKEN':
        monkeypatch.setenv('GITHUB_JOB','render')
        monkeypatch.setenv('NATIVE_PUBLICATION_TOKEN_ORIGIN',credential)
        monkeypatch.setenv('NATIVE_PUBLICATION_PUBLISHING_STEP','native_publication')
        monkeypatch.setenv('GITHUB_WORKFLOW_REF',m.REPOSITORY+'/.github/workflows/render.yml@refs/heads/main')
    stage_api = ExistingIntent(candidate)
    path = m.stage(stage_api, root, 'main', head, 1)
    origin = dict(json.loads(path.read_bytes())['producer_origin'], _repository_id=1)
    merge, observed, tree_sha = 'c' * 40, 'd' * 40, 'e' * 40
    entries = []
    for item in m.projection(root, head):
        if item.mode is not ABSENT:
            entries.append({'path': item.path, 'mode': item.mode, 'sha': item.blob_sha, 'type': 'blob'})
    if state == 'superseded':
        entries[0]['sha'] = 'f' * 40
    if state == 'missing':
        entries.pop()
    class Readback:
        def __init__(self):
            self.effects = []
        def request(self, method, endpoint, body=None):
            assert method == 'GET', 'settlement must never repair or recreate intent'
            if endpoint=='/':return {'id':1,'full_name':m.REPOSITORY}
            if endpoint == '/pulls/7':
                row = copy.deepcopy(stage_api.pull)
                if state != 'pending':
                    row.update(state='closed', merged=True, merge_commit_sha=merge)
                if state == 'wrong_head':
                    row['head']['sha'] = 'f' * 40
                return row
            if endpoint == '/git/ref/heads/main':
                return {'object': {'sha': observed}}
            if endpoint == '/compare/' + merge + '...' + observed:
                return {'status': 'behind' if state == 'wrong_ancestry' else 'ahead'}
            if endpoint == '/git/commits/' + observed:
                return {'sha': observed, 'tree': {'sha': tree_sha}}
            if endpoint == '/git/trees/' + tree_sha:
                return {'sha': tree_sha, 'truncated': state == 'truncated', 'tree': entries}
            raise AssertionError(endpoint)
    monkeypatch.setattr(m, 'protection', lambda *args: {'qualified': 'actual-source-test-fixture'})
    if state == 'pending':
        assert m.publication(Readback(), root, origin) == (m.PENDING, None)
    elif state == 'published':
        status, receipt = m.publication(Readback(), root, origin)
        assert status == 0 and receipt['merge_sha'] == merge
        assert receipt['observed_target_sha'] == observed and receipt['source_head'] == head
        assert receipt['source_head'] != receipt['merge_sha']
        if credential=='ADMIN_GH_TOKEN':
            monkeypatch.setattr(m,'prepare_publication',lambda *args:(m.PENDING,path))
            monkeypatch.setattr(m,'GitHub',lambda *args:Readback())
            assert m.main(['publish','--root',str(root),'--deadline',str(m.time.time()+30)])==0
    else:
        with pytest.raises((m.PublicationHeld, m.PublicationValidationError)):
            m.publication(Readback(), root, origin)


@pytest.mark.parametrize('native_rc,expected,pending', [(80, 0, False), (0, 76, False),
    (77, 77, True), (75, 75, False), (76, 76, False)])
def test_shared_helper_native_status_is_sticky_and_never_direct_fallback(tmp_path, native_rc, expected, pending):
    base = Path(__file__).resolve().parents[1]
    log, output = tmp_path / 'calls', tmp_path / 'outputs'
    script = f'. "{base / "scripts/ci/push_retry.sh"}"\n' + r'''
      push_qledger_preflight() { echo guard >> "$CALLS"; return 0; }
      python3() { echo native >> "$CALLS"; return "$NATIVE_RC"; }
      git() { if [ "$1" = push ]; then echo direct-push >> "$CALLS"; fi; return 0; }
      push_retry_init fixture
      push_attempt
      rc=0; push_do origin HEAD:main || rc=$?
      echo "rc=$rc"
      if push_native_pending; then echo pending; fi
      if [ "$rc" -ne 0 ]; then
        push_abort_rebase
        push_backoff
        if push_attempt; then echo forbidden-second-attempt; fi
        if push_publish_ref_may_delete; then echo forbidden-candidate-deletion; fi
      fi
    '''
    result = subprocess.run(['bash', '-eo', 'pipefail', '-c', script], cwd=tmp_path,
        env={**os.environ, 'CALLS': str(log), 'NATIVE_RC': str(native_rc), 'GITHUB_OUTPUT': str(output)},
        capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert f'rc={expected}\n' in result.stdout
    assert ('pending\n' in result.stdout) is pending
    assert 'forbidden-' not in result.stdout
    assert log.read_text().splitlines() == ['guard', 'native'] + (['direct-push'] if native_rc == 80 else [])


def test_original_qlledger_hold_precedes_native_intent(tmp_path):
    base = Path(__file__).resolve().parents[1]
    script = f'. "{base / "scripts/ci/push_retry.sh"}"\n' + r'''
      push_qledger_preflight() { return 9; }
      python3() { echo forbidden-native-effect; return 80; }
      git() { echo forbidden-push; return 0; }
      push_retry_init fixture
      rc=0; push_do origin HEAD:main || rc=$?
      echo "rc=$rc class=$PUSH_FAIL_CLASS"
    '''
    result = subprocess.run(['bash', '-eo', 'pipefail', '-c', script], cwd=tmp_path,
        capture_output=True, text=True)
    assert 'rc=9 class=qledger-integrity' in result.stdout
    assert 'forbidden-' not in result.stdout


def test_commodity_stage_upload_and_final_gate_preserve_original_budget(tmp_path):
    base = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load((base / '.github/workflows/commodity-sentinel.yml').read_text())
    steps = workflow['jobs']['shock']['steps']
    by_id = {s['id']: s for s in steps if 'id' in s}
    stage, upload, final = [by_id[x] for x in ('native_publication_stage', 'native_publication_origin', 'native_publication')]
    assert steps.index(stage) < steps.index(upload) < steps.index(final)
    assert workflow['jobs']['shock']['timeout-minutes'] == 8
    assert stage['env']['NATIVE_PUBLICATION_PUBLISHING_STEP'] == 'native_publication_stage'
    assert all('continue-on-error' not in s for s in (stage, upload, final))
    assert upload['with']['path'] == '${{ steps.native_publication_stage.outputs.native_origin_path }}'
    assert final['env']['NATIVE_ORIGINAL_RECORD'] == upload['with']['path']
    assert final['env']['NATIVE_ORIGINAL_DEADLINE'] == '${{ steps.native_publication_stage.outputs.native_deadline }}'
    official = upload
    assert official['uses'] == 'actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02'
    assert official['with']['overwrite'] is False
    # Actual final shell refuses pending; upload/staging cannot mint publication.
    output = tmp_path / 'outputs'
    script = 'python3() { return 77; }\n' + final['run']
    result = subprocess.run(['bash', '-eo', 'pipefail', '-c', script], cwd=tmp_path,
        env={**os.environ, 'GITHUB_OUTPUT': str(output), 'NATIVE_ORIGINAL_RECORD': 'original',
             'NATIVE_ORIGINAL_DEADLINE': '123'}, capture_output=True, text=True)
    assert result.returncode == 77
    assert not output.exists()


def test_settlement_checks_original_stage_without_impersonating_final_step(candidate, monkeypatch):
    root, head, _ = candidate
    api = ExistingIntent(candidate)
    path = m.stage(api, root, 'main', head, 1)
    monkeypatch.delenv('NATIVE_PUBLICATION_PUBLISHING_STEP')
    class Repository:
        def request(self, method, endpoint):
            assert (method, endpoint) == ('GET', '/')
            return {'id': 1, 'full_name': m.REPOSITORY}
    observed = []
    def confirmed(api, actual_root, origin):
        observed.append(origin)
        return 0, {'test_scope': 'original-source binding only'}
    monkeypatch.setattr(m, 'publication', confirmed)
    assert m.settle(Repository(), root, path, 5, clock=lambda: 0) == 0
    assert len(observed) == 1 and observed[0]['publishing_step'] == 'native_publication_stage'


def test_fms_origin_names_actual_acquisition_stage_without_impersonating_shock(candidate,monkeypatch):
    root,head,env=candidate
    monkeypatch.setenv('GITHUB_JOB','acquire')
    monkeypatch.setenv('GITHUB_WORKFLOW_REF',m.REPOSITORY+'/.github/workflows/fms-acquire.yml@refs/heads/main')
    api=ExistingIntent(candidate)
    record=m.stage(api,root,'main',head,1)
    origin=json.loads(record.read_bytes())['producer_origin']
    assert origin['workflow_path']=='.github/workflows/fms-acquire.yml'
    assert origin['publishing_job']=='acquire' and origin['publishing_step']=='native_publication_stage'


def test_fms_final_gate_never_turns_pending_into_a_source_handoff(tmp_path):
    base=Path(__file__).resolve().parents[1]
    workflow=yaml.safe_load((base/'.github/workflows/fms-acquire.yml').read_text())
    final=next(s for s in workflow['jobs']['acquire']['steps'] if s.get('id')=='persist')
    output=tmp_path/'outputs'
    result=subprocess.run(['bash','-eo','pipefail','-c','python3() { return 77; }\n'+final['run']],
        env={**os.environ,'NATIVE_ORIGINAL_RECORD':'original','NATIVE_ORIGINAL_CODE':str(tmp_path),
             'RUNNER_TEMP':str(tmp_path),'GITHUB_RUN_ID':'42000000000','GITHUB_RUN_ATTEMPT':'1',
             'GITHUB_OUTPUT':str(output)},capture_output=True,text=True)
    assert result.returncode==77 and not output.exists()


def test_render_local_record_is_never_uploaded_as_app_origin(candidate,monkeypatch):
    root,head,env=candidate
    monkeypatch.setenv('GITHUB_JOB','render')
    monkeypatch.setenv('NATIVE_PUBLICATION_TOKEN_ORIGIN','ADMIN_GH_TOKEN')
    monkeypatch.setenv('NATIVE_PUBLICATION_PUBLISHING_STEP','native_publication')
    monkeypatch.setenv('GITHUB_WORKFLOW_REF',m.REPOSITORY+'/.github/workflows/render.yml@refs/heads/main')
    api=ExistingIntent(candidate)
    path=m.stage(api,root,'main',head,1)
    assert path.name=='publication.json'
    record=json.loads(path.read_bytes())
    assert record['schema']=='mastermind.native-publication-local.v1'
    assert record['producer_origin']['credential_origin']=='ADMIN_GH_TOKEN'
    assert 'mastermind-native-publication-intent:v1' in api.pull['body']
    outputs=Path(env['GITHUB_OUTPUT']).read_text()
    assert 'native_origin_path' not in outputs and 'native_origin_name' not in outputs
    class Repository:
        def request(self,method,endpoint):
            assert (method,endpoint)==('GET','/')
            return {'id':1,'full_name':m.REPOSITORY}
    calls=[]
    monkeypatch.setattr(m,'publication',lambda *args:(calls.append(args[2]) or (m.PENDING,None)))
    ticks=iter((0,0,0,0,5))
    assert m.settle(Repository(),root,path,5,clock=lambda:next(ticks),sleep=lambda _:None)==m.PENDING
    assert len(calls)==1 and calls[0]['credential_origin']=='ADMIN_GH_TOKEN'


def test_render_credential_does_not_fall_back_to_present_app_token(candidate,monkeypatch):
    root,head,env=candidate
    git(root,'remote','add','origin','https://github.com/'+m.REPOSITORY+'.git')
    monkeypatch.setenv('NATIVE_PUBLICATION_TOKEN_ORIGIN','ADMIN_GH_TOKEN')
    monkeypatch.setenv('GITHUB_TOKEN','fake-app-must-not-be-used')
    with pytest.raises(m.PublicationHeld,match='render_authorization_header_missing'):
        m.GitHub(root)


def test_render_native_route_precedes_legacy_rebase_and_retains_candidate_on_pending():
    base=Path(__file__).resolve().parents[1]
    workflow=yaml.safe_load((base/'.github/workflows/render.yml').read_text())
    step=next(s for s in workflow['jobs']['render']['steps'] if s.get('id')=='native_publication')
    body=step['run']
    assert step['env']['ADMIN_GH_TOKEN']=='${{ secrets.ADMIN_GH_TOKEN }}'
    assert step['env']['NATIVE_PUBLICATION_TOKEN_ORIGIN']=='ADMIN_GH_TOKEN'
    assert body.index('native_publication_capture_source')<body.index('push_native_do')<body.index('while push_attempt')
    native=body[body.index('native_initial_rc=0'):body.index('while push_attempt')]
    assert '*) exit "$native_initial_rc"' in native
    assert 'NATIVE_PUBLICATION_EXPECT_OFF=1' in native
    # Original forty-minute budget retained; native admission is not publication.
    assert 'PUSH_BUDGET_SECS=2400' in body


@pytest.mark.parametrize('workflow,job',[('public-render','render'),('daily','cortex'),('engine-render','engine-render')])
@pytest.mark.parametrize('unsettled',[75,77])
def test_active_app_producer_graph_refuses_unsettled_publication(tmp_path,workflow,job,unsettled):
    base=Path(__file__).resolve().parents[1]
    steps=yaml.safe_load((base/f'.github/workflows/{workflow}.yml').read_text())['jobs'][job]['steps']
    byid={s['id']:s for s in steps if 'id' in s}
    stage,upload,final=(byid[k] for k in ('native_publication_stage','native_publication_origin','native_publication'))
    assert steps.index(stage)<steps.index(upload)<steps.index(final)
    assert stage['env']['GITHUB_TOKEN']=='${{ secrets.GITHUB_TOKEN }}'
    assert upload['uses']=='actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02'
    assert all('continue-on-error' not in s for s in (stage,upload,final))
    output=tmp_path/'outputs'
    result=subprocess.run(['bash','-eo','pipefail','-c',f'python3() {{ return {unsettled}; }}\n'+final['run']],
        env={**os.environ,'NATIVE_ORIGINAL_RECORD':'original','NATIVE_ORIGINAL_CODE':str(tmp_path),
             'NATIVE_ORIGINAL_DEADLINE':'123','GITHUB_WORKSPACE':str(tmp_path),'GITHUB_OUTPUT':str(output)},
        capture_output=True,text=True)
    assert result.returncode==unsettled and not output.exists()


def test_explicit_app_rest_reference_never_falls_back_or_repurposes_render_header(candidate, monkeypatch):
    root, _, _ = candidate
    git(root, 'remote', 'add', 'origin', 'https://github.com/' + m.REPOSITORY + '.git')
    git(root, 'config', 'http.https://github.com/.extraheader', 'AUTHORIZATION: Basic fake-render-header')
    monkeypatch.setenv('GITHUB_TOKEN', 'fake-app-token')
    monkeypatch.delenv('NATIVE_PUBLICATION_TOKEN_ORIGIN', raising=False)
    assert m.GitHub(root).authorization == 'Basic fake-render-header'
    monkeypatch.setenv('NATIVE_PUBLICATION_TOKEN_ORIGIN', 'GITHUB_TOKEN')
    assert m.GitHub(root).authorization == 'Bearer fake-app-token'
    monkeypatch.delenv('GITHUB_TOKEN')
    with pytest.raises(m.PublicationHeld, match='app_rest_token_missing'):
        m.GitHub(root)


@pytest.mark.parametrize('mutation', ['helper', 'import', 'local-action'])
def test_actual_post_rebase_execution_uses_original_git_source_frame(tmp_path, mutation):
    """Execute the protected loader and shared helper across a real rebase.

    Only the final legacy Git write is mocked. The original QLedger selector
    and publisher import execute from the captured source, with no API call.
    """
    base = Path(__file__).resolve().parents[1]
    root = tmp_path / 'producer'
    root.mkdir()
    git(root, 'init', '-q', '-b', 'main')
    git(root, 'config', 'user.name', 'fixture')
    git(root, 'config', 'user.email', 'fixture@example.invalid')
    paths = set(m.GUARD_PATHS) | {'scripts/__init__.py', 'scripts/ci/push_retry.sh',
        'scripts/ci/native_queue_push.py', 'scripts/ci/native_publication.py',
        'scripts/ci/native_publication_origin.py', 'scripts/ci/native_publication_source.sh',
        'scripts/ci/fms_persist.py', 'scripts/ci/govrev_source_binding.py',
        '.github/workflows/commodity-sentinel.yml', '.github/actions/native-publication-origin/action.yml'}
    for name in paths:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        source = base / name
        # Missing core files are inert metadata fixtures, never imported in this
        # legacy-only execution test. Actual d89 normalizer compatibility is a
        # separate retained check; this test claims no native readiness.
        target.write_bytes(source.read_bytes() if source.is_file() else b'# inert unexecuted guard fixture\n')
    git(root, 'add', '.')
    git(root, 'commit', '-qm', 'original protected source fixture')
    source_sha = git(root, 'rev-parse', 'HEAD')
    definition = yaml.safe_load((root / '.github/workflows/commodity-sentinel.yml').read_text())
    steps = definition['jobs']['shock']['steps']
    original_stage = next(x for x in steps if x.get('id') == 'native_publication_stage')
    original_upload = next(x for x in steps if x.get('id') == 'native_publication_origin')
    prefix = original_stage['run'].split('python -m scripts.build_commodities', 1)[0]
    assert 'GIT_NO_REPLACE_OBJECTS=1' in prefix and 'git show' in prefix
    git(root, 'checkout', '-qb', 'integration')
    if mutation == 'helper':
        (root / 'scripts/ci/native_queue_push.py').write_text("raise RuntimeError('MUTATED_HELPER_EXECUTED')\n")
        (root / 'scripts/ci/native_publication_source.sh').write_text('echo MUTATED_LOADER_EXECUTED; return 99\n')
    elif mutation == 'import':
        (root / 'scripts/__init__.py').write_text("raise RuntimeError('MUTATED_IMPORT_EXECUTED')\n")
        (root / 'scripts/ci/native_publication_origin.py').write_text("raise RuntimeError('MUTATED_CODEC_EXECUTED')\n")
        (root / 'engine/qledger_store.py').write_text("raise RuntimeError('MUTATED_LEDGER_IMPORT_EXECUTED')\n")
    else:
        (root / '.github/actions/native-publication-origin/action.yml').write_text('runs:\n  using: composite\n  steps:\n    - run: echo MUTATED_ACTION_EXECUTED\n      shell: bash\n')
        workflow_path = root / '.github/workflows/commodity-sentinel.yml'
        workflow_path.write_text(workflow_path.read_text().replace(
            'actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02', './.github/actions/native-publication-origin'))
    git(root, 'add', '.')
    git(root, 'commit', '-qm', 'new unrelated checkout version')
    git(root, 'checkout', '-qb', 'producer', source_sha)
    (root / 'generated.json').write_text('original acquisition, never rerun')
    git(root, 'add', 'generated.json')
    git(root, 'commit', '-qm', 'original generated output')
    git(root, 'remote', 'add', 'origin', str(tmp_path / 'not-contacted.git'))
    runner = tmp_path / 'runner'
    runner.mkdir()
    body = prefix + r'''
      git rebase integration
      git() { if [ "$1" = push ]; then echo LOCAL_FIXTURE_WRITE; return 0; fi; command git "$@"; }
      push_retry_init fixture
      push_attempt
      push_do origin HEAD:main
      echo ORIGINAL_SOURCE_FRAME_SUCCEEDED
    '''
    result = subprocess.run(['bash', '-eo', 'pipefail', '-c', body], cwd=root,
        env={**os.environ, 'GITHUB_WORKSPACE': str(root), 'GITHUB_WORKFLOW_SHA': source_sha,
             'GITHUB_SHA': source_sha, 'GITHUB_RUN_ID': '42', 'GITHUB_RUN_ATTEMPT': '1',
             'GITHUB_JOB': 'shock', 'RUNNER_TEMP': str(runner)}, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'ORIGINAL_SOURCE_FRAME_SUCCEEDED' in result.stdout
    assert 'LOCAL_FIXTURE_WRITE' in result.stdout
    assert 'MUTATED_' not in result.stdout + result.stderr
    frame = runner / 'native-publication-code-42-1-shock'
    assert (frame / 'scripts/ci/native_queue_push.py').read_bytes() == subprocess.run(
        ['git', '-C', str(root), 'show', source_sha + ':scripts/ci/native_queue_push.py'],
        check=True, capture_output=True).stdout
    assert original_upload['uses'] == 'actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02'
    if mutation in ('helper', 'import'):
        # The pre-repair -m import path would execute the substituted checkout.
        unsafe = subprocess.run(['python3', '-m', 'scripts.ci.native_queue_push', 'publish'],
            cwd=root, env={**os.environ, 'PYTHONPATH': str(frame)}, capture_output=True, text=True)
        assert unsafe.returncode != m.LEGACY and 'MUTATED_' in unsafe.stderr
