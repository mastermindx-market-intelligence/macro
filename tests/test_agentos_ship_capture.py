"""W4 assists ordinary authored records; it cannot decide whether work may run."""
from __future__ import annotations
import copy
import datetime as dt
import json
from pathlib import Path
import pytest
import yaml

BODY = ('Workstream: WS:ALPHA\nLinear: NONE\nPortfolio-Mode: tracked\n'
        'Wave: W1\nAuthority: implementation\nCompletion: built-not-proven\n\n## Change\n')
BRANCH = 'claude/alpha'
NOW = dt.datetime(2026, 10, 4, tzinfo=dt.timezone.utc)


def record(root, key='ALPHA', claim=True, owns=None):
    p = root / 'agentos/workstreams' / f'WS-{key}.md'
    p.parent.mkdir(parents=True, exist_ok=True)
    rec = dict(key=key, title='A', objective='An observable result', status='active',
               program='project-active-build-control', repos=['macro'], owner='chairman',
               **{'class': 'build'}, blast_radius='reversible', ambiguity='specified',
               waves=[dict(id='W1', title='One', status='in_progress')],
               next_action='Ship the scoped change', owns_paths=owns or ['lib/alpha/**'])
    if claim:
        rec['claim'] = dict(by=BRANCH, at='2026-10-03T20:00:00Z', expires='2026-10-04T08:00:00Z')
    p.write_text('---\n' + yaml.safe_dump(rec, sort_keys=False) + '---\n\nKeep this prose.\n')
    return p


def capture(root, **extra):
    from scripts.agentos_ship_capture import capture_pr
    return capture_pr(root, branch=BRANCH, body=BODY, pr=123, paths=['lib/alpha/x.py'],
                      now=NOW, **extra)


def frontmatter(p):
    return yaml.safe_load(p.read_text().split('---', 2)[1])


def test_exact_claim_captures_existing_wave_and_preserves_knowledge_boundaries(tmp_path):
    p = record(tmp_path)
    before = frontmatter(p)
    result = capture(tmp_path)
    assert result['code'] == 'CAPTURE_UNCOMMITTED'
    after = frontmatter(p)
    assert after['waves'][0]['pr'] == 123
    assert after['waves'][0]['status'] == 'awaiting_ci'
    expected = copy.deepcopy(before)
    expected['waves'][0].update(pr=123, status='awaiting_ci')
    assert after == expected
    assert p.read_text().endswith('\nKeep this prose.\n')
    assert capture(tmp_path)['code'] == 'CAPTURE_UNCHANGED'


@pytest.mark.parametrize('mode', ['missing', 'malformed', 'multiple_claims', 'body_mismatch',
                                  'unowned', 'multiple_owners', 'conflicting_pr', 'terminal'])
def test_unknown_ambiguous_and_conflicting_identity_never_mutates(tmp_path, mode):
    p = record(tmp_path, claim=mode not in {'unowned', 'multiple_owners'})
    body = BODY
    if mode == 'missing':
        p.unlink()
    elif mode == 'malformed':
        p.write_text('---\nkey: [broken\n---\n')
    elif mode == 'multiple_claims':
        record(tmp_path, 'BETA')
    elif mode == 'body_mismatch':
        body = BODY.replace('WS:ALPHA', 'WS:BETA')
    elif mode == 'unowned':
        p.write_text(p.read_text().replace('lib/alpha/**', 'engine/other/**'))
    elif mode == 'multiple_owners':
        record(tmp_path, 'BETA', claim=False)
    elif mode == 'conflicting_pr':
        p.write_text(p.read_text().replace('status: in_progress', 'status: in_progress\n  pr: 999'))
    elif mode == 'terminal':
        p.write_text(p.read_text().replace('status: in_progress', 'status: done'))
    before = {str(x): x.read_bytes() for x in tmp_path.rglob('*') if x.is_file()}
    from scripts.agentos_ship_capture import capture_pr
    result = capture_pr(tmp_path, branch=BRANCH, body=body, pr=123,
                        paths=['lib/alpha/x.py'], now=NOW)
    assert result['changed'] is False
    assert {str(x): x.read_bytes() for x in tmp_path.rglob('*') if x.is_file()} == before
    assert 'decision' not in result


def test_unique_path_binding_and_expired_claim_do_not_grant_liveness(tmp_path):
    p = record(tmp_path, claim=False)
    assert capture(tmp_path)['code'] == 'CAPTURE_UNCOMMITTED'
    q = record(tmp_path)
    q.write_text(q.read_text().replace('2026-10-04T08:00:00Z', '2026-10-03T21:00:00Z'))
    # Expired claim is not a current binding; the exact path may still bind.
    assert capture(tmp_path)['binding'] == 'paths'


def test_release_cannot_erase_another_advisory_claim(tmp_path):
    from scripts.agentos_ship_capture import edit_claim
    p = record(tmp_path)
    before = p.read_bytes()
    result = edit_claim(tmp_path, workstream='ALPHA', branch='claude/other', release=True, now=NOW)
    assert result['changed'] is False
    assert p.read_bytes() == before
    assert edit_claim(tmp_path, workstream='ALPHA', branch=BRANCH, release=True, now=NOW)['changed']
    assert 'claim' not in frontmatter(p)


def test_symlink_target_is_report_only_noop(tmp_path):
    p = record(tmp_path)
    external = tmp_path / 'outside.md'
    p.rename(external)
    p.symlink_to(external)
    before = external.read_bytes()
    assert capture(tmp_path)['changed'] is False
    assert external.read_bytes() == before


def test_hook_ignores_unrecognized_commands_without_inspecting_store(tmp_path):
    from scripts.agentos_ship_capture import hook_event
    for command in ['echo hello', 'gh pr create --fill', 'gh pr create --body-file b; touch x',
                    'gh pr create --repo foreign/repo --body-file b',
                    'gh pr create --head other --body-file b', 'gh pr create --body "$(cat b)"']:
        r = hook_event(tmp_path, {'hook_event_name': 'PostToolUse', 'tool_name': 'Bash',
                                  'tool_input': {'command': command}, 'tool_response': {'stdout': 'bad'}})
        assert not r['changed']
        assert 'decision' not in r
    assert list(tmp_path.iterdir()) == []


def test_successful_creation_is_bound_to_local_branch_repo_and_submitted_body(tmp_path, monkeypatch):
    from scripts import agentos_ship_capture as s
    p = record(tmp_path)
    (tmp_path / 'pr-body.md').write_text(BODY)
    def git(root, *args):
        if args == ('branch', '--show-current'):
            return BRANCH
        if args == ('remote', 'get-url', 'origin'):
            return 'git@github.com:mastermindx-market-intelligence/macro.git'
        if args[0] == 'diff':
            return 'M\0lib/alpha/x.py\0'
        raise AssertionError(args)
    monkeypatch.setattr(s, '_git', git)
    payload = {'hook_event_name': 'PostToolUse', 'tool_name': 'Bash',
               'tool_input': {'command': 'gh pr create --title Change --body-file pr-body.md'},
               'tool_response': {'stdout': 'https://github.com/mastermindx-market-intelligence/macro/pull/123\n',
                                 'stderr': '', 'interrupted': False}}
    assert s.hook_event(tmp_path, payload, now=NOW)['changed'] is True
    assert frontmatter(p)['waves'][0]['pr'] == 123


@pytest.mark.parametrize('bad', ['url', 'branch', 'failure'])
def test_creation_identity_mismatch_does_not_write(tmp_path, monkeypatch, bad):
    from scripts import agentos_ship_capture as s
    p = record(tmp_path)
    monkeypatch.setattr(s, '_git', lambda root, *args: '' if bad == 'branch' else
                        BRANCH if args[0] == 'branch' else 'git@github.com:org/macro.git')
    payload = {'hook_event_name': 'PostToolUse', 'tool_name': 'Bash',
               'tool_input': {'command': "gh pr create --title Change --body '" + BODY + "'"},
               'tool_response': {'stdout': 'https://github.com/' + ('wrong' if bad == 'url' else 'org') + '/macro/pull/123',
                                 'interrupted': bad == 'failure'}}
    before = p.read_bytes()
    assert not s.hook_event(tmp_path, payload, now=NOW)['changed']
    assert p.read_bytes() == before


def test_capture_rejects_body_file_that_traverses_outside_repository(tmp_path):
    from scripts import agentos_ship_capture as s
    root = tmp_path / 'repo'
    root.mkdir()
    (tmp_path / 'outside.md').write_text(BODY)
    assert s._creation_body(root, 'gh pr create --body-file ../outside.md') is None


@pytest.mark.parametrize('stamp,expected', [
    ('2026-10-03T19:59:59Z', 'HANDOFF_REMINDER'),
    ('2026-10-03T20:00:00Z', 'HANDOFF_COMMITTED'),
    ('2026-10-04T00:00:00Z', 'HANDOFF_COMMITTED'),
    ('not-a-date', 'HANDOFF_REMINDER'),
])
def test_valid_committed_same_branch_handoff_clears_reminder(tmp_path, monkeypatch, stamp, expected):
    from scripts import agentos_ship_capture as s
    record(tmp_path)
    directory = tmp_path / 'agentos/handoffs'
    directory.mkdir()
    handoff = dict(workstream='WS:ALPHA', session=BRANCH, model='codex', ended_because='complete',
                   mission='Ship a bounded change', state_before='Existing record',
                   changed=[dict(path='lib/alpha/x.py', what='Implement the change')], prs=[123],
                   verified=[dict(claim='Focused tests pass', command='pytest focused', result='pass')],
                   unverified=[], decisions=[], discoveries=[], unresolved=['None for this accepted scope'], next_actions=['Retain the accepted record'],
                   do_not_redo=['Do not rebuild the accepted work'], danger_areas=['Preserve source custody'])
    path = directory / 'ALPHA-2026-10-04.md'
    path.write_text('---\n' + yaml.safe_dump(handoff, sort_keys=False) + '---\n\nDurable handoff.\n')
    monkeypatch.setattr(s, '_git', lambda root, *args: stamp if args[0] == 'log' else '')
    assert s.handoff_reminder(tmp_path, branch=BRANCH, now=NOW)['code'] == expected
    handoff['session'] = 'claude/old-branch'
    path.write_text('---\n' + yaml.safe_dump(handoff, sort_keys=False) + '---\n')
    assert s.handoff_reminder(tmp_path, branch=BRANCH, now=NOW)['code'] == 'HANDOFF_REMINDER'


def test_agentos_hook_errors_do_not_change_existing_stop_result(monkeypatch, tmp_path, capsys):
    from tests.test_ship_loop_guard import GUARD
    payload = {'hook_event_name': 'Stop'}
    monkeypatch.setattr(GUARD, '_load_payload_and_raw', lambda: (payload, b'{}'))
    monkeypatch.setattr(GUARD, '_delegate_to_evaluated_hook', lambda *a: False)
    monkeypatch.setattr(GUARD, '_repo_root', lambda p: tmp_path)
    monkeypatch.setattr(GUARD, '_state_path', lambda *a: tmp_path / 'state')
    monkeypatch.setattr(GUARD, '_stop', lambda *a: GUARD._emit({'decision': 'block', 'reason': 'unchanged'}))
    def timeout(*a, **k):
        raise __import__('subprocess').TimeoutExpired('agentos', 5)
    monkeypatch.setattr(GUARD.subprocess, 'run', timeout)
    GUARD.main()
    assert json.loads(capsys.readouterr().out) == {'decision': 'block', 'reason': 'unchanged'}
    # The adapter itself must be tested: pre-change main alone would be green.
    GUARD._agentos_assist(tmp_path, payload)
    assert capsys.readouterr().out == ''
    assert not (tmp_path / 'state').exists()


@pytest.mark.parametrize('value', ['null', '~'])
def test_existing_null_pr_field_is_not_duplicated(tmp_path, value):
    p = record(tmp_path)
    p.write_text(p.read_text().replace('status: in_progress', 'status: in_progress\n  pr: ' + value))
    before = p.read_bytes()
    assert capture(tmp_path)['changed'] is False
    assert p.read_bytes() == before


def test_path_collection_retains_both_rename_owners(tmp_path, monkeypatch):
    from scripts import agentos_ship_capture as s
    monkeypatch.setattr(s, '_git', lambda *a: 'R100\0old/source.py\0lib/alpha/new.py\0M\0lib/alpha/x.py\0')
    assert s._paths(tmp_path) == ['old/source.py', 'lib/alpha/new.py', 'lib/alpha/x.py']


@pytest.mark.parametrize('paths', [['../outside'], ['/absolute'], ['x\\bad'], ['x\0bad']])
def test_exact_claim_never_accepts_unsafe_path_evidence(tmp_path, paths):
    from scripts.agentos_ship_capture import capture_pr
    p = record(tmp_path)
    before = p.read_bytes()
    assert not capture_pr(tmp_path, branch=BRANCH, body=BODY, pr=123, paths=paths, now=NOW)['changed']
    assert p.read_bytes() == before


def test_stop_report_delegates_only_to_same_repository_evaluated_worktree(tmp_path, monkeypatch, capsys):
    from scripts import agentos_ship_capture as s
    import argparse, io, subprocess
    source, target = tmp_path / 'source', tmp_path / 'target'
    source.mkdir(); target.mkdir()
    (target / 'scripts').mkdir()
    (target / 'scripts/agentos.py').write_text('# trusted same-repository target')
    monkeypatch.setattr(s.aos, '_ROOT', source)
    monkeypatch.setattr(s.sys, 'stdin', io.StringIO(json.dumps({'hook_event_name':'Stop','cwd':str(target)})))
    monkeypatch.setattr(s, '_git', lambda root, *args: str(target) if '--show-toplevel' in args else str(tmp_path / 'common.git'))
    calls = []
    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, '{}\n', '')
    monkeypatch.setattr(s.subprocess, 'run', run)
    args = argparse.Namespace(repo=None, hook=True, command='ship-report')
    assert s.command(args) == 0
    assert json.loads(capsys.readouterr().out) == {}
    assert calls[0][0][1] == str(target / 'scripts/agentos.py')
    assert calls[0][0][2:] == ['ship-report','--hook']
    assert json.loads(calls[0][1]['input'])['_agentos_delegated'] is True


@pytest.mark.parametrize('raw', ['not json', '{' * 1048577, '[]'], ids=['invalid-json', 'oversized', 'non-object'])
def test_stop_hook_malformed_input_is_native_empty_response(monkeypatch, capsys, raw):
    from scripts import agentos_ship_capture as s
    import argparse, io
    monkeypatch.setattr(s.sys, 'stdin', io.StringIO(raw))
    assert s.command(argparse.Namespace(repo=None, hook=True, command='ship-report')) == 0
    assert json.loads(capsys.readouterr().out) == {}


@pytest.mark.parametrize('bad', ['foreign', 'missing', 'delegated'])
def test_stop_delegation_rejects_foreign_missing_and_second_hop(tmp_path, monkeypatch, capsys, bad):
    from scripts import agentos_ship_capture as s
    import argparse, io
    source, target = tmp_path / 'source', tmp_path / 'target'
    source.mkdir(); target.mkdir()
    (target / 'scripts').mkdir()
    if bad != 'missing':
        (target / 'scripts/agentos.py').write_text('# trusted source')
    monkeypatch.setattr(s.aos, '_ROOT', source)
    payload = {'hook_event_name': 'Stop', 'cwd': str(target), '_agentos_delegated': bad == 'delegated'}
    monkeypatch.setattr(s.sys, 'stdin', io.StringIO(json.dumps(payload)))
    def git(root, *args):
        if '--show-toplevel' in args:
            return str(target)
        return str(root / 'foreign.git') if bad == 'foreign' else str(tmp_path / 'common.git')
    monkeypatch.setattr(s, '_git', git)
    def run(*args, **kwargs):
        pytest.fail('Rejected delegation must not start a child')
    monkeypatch.setattr(s.subprocess, 'run', run)
    assert s.command(argparse.Namespace(repo=None, hook=True, command='ship-report')) == 0
    assert json.loads(capsys.readouterr().out) == {}


def test_wave_identity_uses_frozen_canonical_length_limit():
    from scripts import agentos_ship_capture as s
    with pytest.raises(ValueError, match='wave'):
        s._header(BODY.replace('Wave: W1', 'Wave: ' + 'W' * 65))
