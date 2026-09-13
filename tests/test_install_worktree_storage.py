"""Host installation preserves unrelated app settings and existing hooks."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts import install_worktree_storage as installer


def test_staged_install_preserves_settings_and_records_reversible_fields(tmp_path):
    home = tmp_path / 'home'
    profile = home / 'Library/Application Support/Claude-3/claude_desktop_config.json'
    cli = home / '.claude/settings.json'
    codex = home / '.codex/hooks.json'
    old_hook = {'hooks': [{'type': 'command', 'command': 'existing-hook'}]}
    for path, content in (
        (profile, {'preferences': {'unrelated': 'keep'}, 'accountField': 'keep'}),
        (cli, {'theme': 'dark', 'hooks': {'WorktreeCreate': [old_hook]}}),
        (codex, {'description': 'keep', 'hooks': {'SessionStart': [old_hook]}}),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(content))
    mount = tmp_path / 'SSD'; mount.mkdir()
    policy_path = home / '.config/mastermind/worktree-storage.json'
    info = dict(VolumeUUID='approved', MountPoint=str(mount), Internal=False, Writable=True, FilesystemType='apfs')
    with patch.object(Path, 'home', return_value=home), patch.object(installer.storage, 'POLICY_PATH', policy_path), patch.object(installer.storage, 'volume_info', return_value=info), patch('sys.argv', ['install', '--apply', '--without-create-hook', '--mount', str(mount), '--volume-uuid', 'approved', '--min-free-gib', '0']):
        installer.main()
    native = json.loads(profile.read_text())
    assert native['accountField'] == 'keep'
    assert native['preferences'] == {'unrelated': 'keep', 'chillingSlothLocation': {'customPath': str(mount / 'agent-workspaces/claude')}}
    claude = json.loads(cli.read_text())
    assert claude['theme'] == 'dark'
    assert claude['hooks']['WorktreeCreate'] == [old_hook]
    assert len(claude['hooks']['SessionStart']) == 1
    codex_config = json.loads(codex.read_text())
    assert codex_config['description'] == 'keep'
    assert codex_config['hooks']['SessionStart'][0] == old_hook
    assert len(codex_config['hooks']['SessionStart']) == 2
    receipt = json.loads(next((mount / 'agent-workspaces/backups').glob('*/receipt.json')).read_text())
    assert receipt['status'] == 'APPLIED'
    assert receipt['creation_hook'] == 'DEFERRED'
    assert not receipt['helper_previously_present']
    assert not receipt['policy_previously_present']
    assert receipt['changes'][0]['before'] == {'present': False, 'value': None}


def test_concurrent_settings_change_is_not_overwritten(tmp_path):
    path = tmp_path / 'config.json'; path.write_bytes(b'new writer')
    try:
        installer.write_if_unchanged(path, b'old value', b'our change')
    except RuntimeError as exc:
        assert 'concurrent settings update' in str(exc)
    else:
        raise AssertionError('concurrent update accepted')
    assert path.read_bytes() == b'new writer'


@pytest.fixture
def session_install(tmp_path, monkeypatch):
    home = tmp_path / 'home'
    mount = tmp_path / 'SSD'
    mount.mkdir()
    paths = {'claude': home / '.claude/settings.json', 'codex': home / '.codex/hooks.json'}
    library = home / '.local/lib/mastermind/worktree-storage/worktree_storage.py'
    policy = home / '.config/mastermind/worktree-storage.json'
    command = f'python3 "{library}" session-start'
    unrelated = {'matcher': 'resume', 'hooks': [{'type': 'command', 'command': 'keep-me'}]}
    for path in paths.values():
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({'unrelated': True, 'hooks': {'SessionStart': [unrelated]}}))
    monkeypatch.setattr(Path, 'home', lambda: home)
    monkeypatch.setattr(installer.storage, 'POLICY_PATH', policy)
    monkeypatch.setattr(installer.storage, 'volume_info', lambda _: dict(
        VolumeUUID='approved', MountPoint=str(mount), Internal=False,
        Writable=True, FilesystemType='apfs'))
    monkeypatch.setattr('sys.argv', ['install', '--apply', '--without-create-hook',
                                    '--mount', str(mount), '--volume-uuid', 'approved',
                                    '--min-free-gib', '0'])
    calls = []

    def run():
        stamp = datetime(2030, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=len(calls))
        calls.append(stamp)
        with patch.object(installer, 'datetime') as clock:
            clock.now.return_value = stamp
            installer.main()

    return dict(home=home, paths=paths, library=library, policy=policy,
                command=command, unrelated=unrelated, run=run)


@pytest.mark.parametrize('client', ['claude', 'codex'])
@pytest.mark.parametrize('kind', ['compact', 'wrong-type'])
def test_session_start_restricted_or_wrong_type_cannot_suppress_protection(session_install, client, kind):
    case = session_install
    path = case['paths'][client]
    misleading = {'hooks': [{'type': 'command', 'command': case['command']}]}
    if kind == 'compact':
        misleading['matcher'] = 'compact'
    else:
        misleading['hooks'][0]['type'] = 'prompt'
        misleading['hooks'][0]['prompt'] = 'unrelated prompt'
    config = json.loads(path.read_text())
    config['hooks']['SessionStart'].append(misleading)
    path.write_text(json.dumps(config))
    case['run']()
    after = json.loads(path.read_text())
    groups = after['hooks']['SessionStart']
    assert after['unrelated'] is True
    assert groups[:2] == [case['unrelated'], misleading]
    assert len(groups) == 3
    assert groups[2].get('matcher', '') == ''
    assert groups[2]['hooks'][0]['type'] == 'command'
    assert groups[2]['hooks'][0]['command'] == case['command']


@pytest.mark.parametrize('client', ['claude', 'codex'])
@pytest.mark.parametrize('matcher', [None, ''])
def test_session_start_valid_unconditional_install_is_idempotent(session_install, client, matcher):
    case = session_install
    path = case['paths'][client]
    valid = {'hooks': [{'type': 'command', 'command': case['command'], 'timeout': 300}]}
    if matcher is not None:
        valid['matcher'] = matcher
    config = json.loads(path.read_text())
    config['hooks']['SessionStart'].append(valid)
    path.write_text(json.dumps(config))
    case['run']()
    first = {key: value.read_bytes() for key, value in case['paths'].items()}
    case['run']()
    assert {key: value.read_bytes() for key, value in case['paths'].items()} == first
    assert json.loads(path.read_text())['hooks']['SessionStart'] == [case['unrelated'], valid]


@pytest.mark.parametrize('client', ['claude', 'codex'])
@pytest.mark.parametrize('invalid', [
    [], {'hooks': []}, {'hooks': {'SessionStart': {}}},
    {'hooks': {'SessionStart': [None]}},
    {'hooks': {'SessionStart': [{'hooks': {}}]}},
    {'hooks': {'SessionStart': [{'hooks': [None]}]}},
    {'hooks': {'SessionStart': [{'matcher': 42, 'hooks': []}]}},
])
def test_session_start_malformed_shape_refuses_before_install_writes(session_install, client, invalid):
    case = session_install
    case['paths'][client].write_text(json.dumps(invalid))
    for key in ('library', 'policy'):
        case[key].parent.mkdir(parents=True, exist_ok=True)
        case[key].write_bytes(b'previous installed bytes\n')
    profile = case['home'] / 'Library/Application Support/Claude/claude_desktop_config.json'
    profile.parent.mkdir(parents=True)
    profile.write_text('{"preferences":{"unrelated":"keep"}}')
    preserved = [*case['paths'].values(), case['library'], case['policy'], profile]
    before = {p: p.read_bytes() for p in preserved}
    with pytest.raises(RuntimeError, match='reconciliation'):
        case['run']()
    assert {p: p.read_bytes() for p in preserved} == before
    assert not (case['home'] / '.codex/AGENTS.md').exists()
    assert not (case['home'] / '.claude/CLAUDE.md').exists()
