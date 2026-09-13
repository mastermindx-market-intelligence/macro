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


_COMMON_BAD_COMMAND_FIELDS = [
    ('missing-command', 'command', None), ('empty-command', 'command', ''),
    ('blank-command', 'command', ' \t\n'),
    ('timeout-object', 'timeout', {}), ('timeout-string', 'timeout', '30'),
    ('timeout-bool', 'timeout', True), ('timeout-null', 'timeout', None),
    ('timeout-nan', 'timeout', float('nan')), ('timeout-infinite', 'timeout', float('inf')),
    ('status-object', 'statusMessage', {}), ('status-null', 'statusMessage', None),
    ('async-string', 'async', 'false'), ('async-number', 'async', 0),
    ('async-null', 'async', None),
]
_CLIENT_BAD_COMMAND_FIELDS = [
    ('codex', 'fractional-timeout', 'timeout', 1.5),
    ('codex', 'negative-timeout', 'timeout', -1),
    ('codex', 'overflow-timeout', 'timeout', 2**64),
    ('codex', 'context-object', 'additionalContextLimit', {}),
    ('codex', 'context-bool', 'additionalContextLimit', True),
    ('codex', 'context-negative', 'additionalContextLimit', -1),
    ('codex', 'context-fractional', 'additionalContextLimit', 0.5),
    ('codex', 'context-overflow', 'additionalContextLimit', 2**64),
    ('codex', 'windows-command-object', 'commandWindows', {}),
    ('codex', 'windows-command-null', 'commandWindows', None),
    ('claude', 'rewake-number', 'asyncRewake', 0),
    ('claude', 'once-string', 'once', 'true'),
    ('claude', 'args-string', 'args', 'script.py'),
    ('claude', 'args-nonstring', 'args', ['script.py', 3]),
    ('claude', 'shell-unknown', 'shell', 'zsh'),
    ('claude', 'condition-object', 'if', {}),
]


@pytest.mark.parametrize('client,case_name,field,value', [
    (client, name, field, value)
    for client in ('claude', 'codex') for name, field, value in _COMMON_BAD_COMMAND_FIELDS
] + _CLIENT_BAD_COMMAND_FIELDS)
def test_command_leaf_refusal_precedes_every_install_write(session_install, client, case_name, field, value):
    case = session_install
    hook = {'type': 'command', 'command': case['command']}
    if case_name == 'missing-command':
        del hook['command']
    else:
        hook[field] = value
    path = case['paths'][client]
    config = json.loads(path.read_text())
    config['hooks']['SessionStart'].append({'hooks': [hook]})
    path.write_text(json.dumps(config))
    for key in ('library', 'policy'):
        case[key].parent.mkdir(parents=True, exist_ok=True)
        case[key].write_bytes(b'preserved installation\n')
    profile = case['home'] / 'Library/Application Support/Claude/claude_desktop_config.json'
    profile.parent.mkdir(parents=True)
    profile.write_text('{"preferences":{"unrelated":"keep"}}')
    for instruction in (case['home'] / '.codex/AGENTS.md', case['home'] / '.claude/CLAUDE.md'):
        instruction.write_text('preserved instructions\n')
    root = case['home'].parent

    def snapshot():
        return {str(p.relative_to(root)): p.read_bytes() if p.is_file() else None
                for p in root.rglob('*')}

    before = snapshot()
    refused = AssertionError('installation write reached before command-field refusal')
    with patch.object(Path, 'mkdir', side_effect=refused), \
         patch.object(Path, 'write_text', side_effect=refused), \
         patch.object(Path, 'write_bytes', side_effect=refused), \
         patch.object(installer, 'write_if_unchanged', side_effect=refused), \
         pytest.raises(RuntimeError, match='reconciliation'):
        case['run']()
    assert snapshot() == before  # Includes backup/receipt directories and all installed files.


@pytest.mark.parametrize('client,options', [
    ('codex', {'timeout': 300, 'async': True, 'statusMessage': '',
               'commandWindows': 'py startup.py', 'additionalContextLimit': 0}),
    ('codex', {'timeout': 0, 'async': False, 'additionalContextLimit': 5000}),
    ('claude', {'timeout': 0.5, 'async': True, 'asyncRewake': False,
                'once': True, 'statusMessage': 'Preparing workspace', 'shell': 'bash'}),
])
def test_valid_command_execution_fields_survive_idempotent_install(session_install, client, options):
    case = session_install
    path = case['paths'][client]
    config = json.loads(path.read_text())
    valid = {'type': 'command', 'command': case['command'], **options,
             'futureMetadata': {'preserve': ['opaque']}}
    config['hooks']['SessionStart'].append({'hooks': [valid]})
    if client == 'claude':
        config['hooks']['SessionStart'].append({'hooks': [
            {'type': 'command', 'command': 'python3', 'args': ['notes.py'],
             'shell': 'powershell', 'if': 'Bash(git status)', 'asyncRewake': True}]})
    path.write_text(json.dumps(config))
    case['run']()
    first = path.read_bytes()
    assert json.loads(first)['hooks'] == config['hooks']
    case['run']()
    assert path.read_bytes() == first


@pytest.mark.parametrize('options', [{'args': []}, {'if': 'Bash(git status)'}])
def test_claude_execution_mode_cannot_mask_shell_startup_hook(session_install, options):
    case = session_install
    path = case['paths']['claude']
    config = json.loads(path.read_text())
    existing = {'hooks': [{'type': 'command', 'command': case['command'], **options}]}
    config['hooks']['SessionStart'].append(existing)
    path.write_text(json.dumps(config))
    case['run']()
    groups = json.loads(path.read_text())['hooks']['SessionStart']
    assert groups[:2] == [case['unrelated'], existing]
    assert len(groups) == 3
    assert groups[2] == {'hooks': [{'type': 'command', 'command': case['command'], 'timeout': 300}]}
    first = path.read_bytes()
    case['run']()
    assert path.read_bytes() == first
