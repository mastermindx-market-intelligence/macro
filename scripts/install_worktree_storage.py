#!/usr/bin/env python3
"""Install the reviewed host storage adapter and Claude settings; report by default.

Never edits Codex app state, shared checkouts, credentials, runner services or
workload concurrency. Backups contain only the specific settings being changed.
"""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
from datetime import datetime, timezone

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

try:
    from scripts import worktree_storage as storage
except ModuleNotFoundError:
    import worktree_storage as storage


def write_if_unchanged(path, before, after):
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
    fd, tmp = tempfile.mkstemp(prefix='.storage-install-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(after)
        os.chmod(tmp, mode)
        if (path.read_bytes() if path.exists() else None) != before:
            raise RuntimeError(f'concurrent settings update: {path}')
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def validate_command_hook(hook, *, codex):
    """Validate documented execution fields without rewriting unrelated metadata.

    Codex: https://learn.chatgpt.com/docs/config-schema.json (HookHandlerConfig).
    Claude: https://code.claude.com/docs/en/hooks#command-hook-fields.
    Claude accepts numeric timeouts; Codex uses unsigned integer seconds.
    """
    def require(valid, field):
        if not valid:
            raise RuntimeError(f'SessionStart settings need reconciliation: invalid command hook {field}')

    require(isinstance(hook.get('command'), str) and bool(hook['command'].strip()), 'command')
    if 'timeout' in hook:
        value = hook['timeout']
        if codex:
            valid = type(value) is int and 0 <= value < 2**64
        else:
            try:
                valid = type(value) in (int, float) and math.isfinite(value)
            except OverflowError:
                valid = False
        require(valid, 'timeout')
    strings = ('statusMessage', 'commandWindows') if codex else ('statusMessage', 'if')
    booleans = ('async',) if codex else ('async', 'asyncRewake', 'once')
    for field in strings:
        if field in hook:
            require(isinstance(hook[field], str), field)
    for field in booleans:
        if field in hook:
            require(type(hook[field]) is bool, field)
    if codex:
        if 'additionalContextLimit' in hook:
            value = hook['additionalContextLimit']
            require(type(value) is int and 0 <= value < 2**64, 'additionalContextLimit')
    else:
        if 'args' in hook:
            require(isinstance(hook['args'], list)
                    and all(isinstance(arg, str) for arg in hook['args']), 'args')
        if 'shell' in hook:
            require(hook['shell'] in ('bash', 'powershell'), 'shell')


def reconcile_session_start(original, command, *, codex=False):
    """Prepare startup coverage without letting restricted/non-command hooks mask it."""
    def malformed():
        raise RuntimeError('SessionStart settings need reconciliation: malformed hook shape')

    if not isinstance(original, dict):
        malformed()
    config = copy.deepcopy(original)
    hooks = config.setdefault('hooks', {})
    if not isinstance(hooks, dict):
        malformed()
    groups = hooks.setdefault('SessionStart', [])
    if not isinstance(groups, list):
        malformed()
    covered = False
    for group in groups:
        if (not isinstance(group, dict) or not isinstance(group.get('hooks'), list)
                or not isinstance(group.get('matcher', ''), str)):
            malformed()
        for hook in group['hooks']:
            if (not isinstance(hook, dict) or not isinstance(hook.get('type'), str)
                    or ('command' in hook and not isinstance(hook['command'], str))):
                malformed()
            if hook['type'] == 'command':
                validate_command_hook(hook, codex=codex)
            # Claude's args form treats command as an executable, not this
            # shell string. Its tool-only `if` condition never fires on SessionStart.
            shell_startup = codex or ('args' not in hook and 'if' not in hook)
            # Startup protection must finish before work begins on every session.
            # Claude's once removes the hook; asyncRewake implies background execution.
            persistent_sync = (not hook.get('async', False)
                               and (codex or not (hook.get('once', False)
                                                  or hook.get('asyncRewake', False))))
            if (group.get('matcher', '') == '' and hook['type'] == 'command'
                    and hook.get('command') == command and shell_startup and persistent_sync):
                covered = True
    if not covered:
        hook = dict(type='command', command=command, timeout=300)
        if codex:
            hook['statusMessage'] = 'Checking external worktree storage'
        groups.append(dict(hooks=[hook]))
    return config


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--without-create-hook', action='store_true',
                    help='stage settings/helper/startup protection while existing project creators await activation')
    ap.add_argument('--mount', type=Path, required=True)
    ap.add_argument('--volume-uuid', required=True)
    ap.add_argument('--min-free-gib', type=int, default=100)
    args = ap.parse_args()
    policy = dict(version=1, mount_point=str(args.mount), volume_uuid=args.volume_uuid,
                  root=str(args.mount / 'agent-workspaces'), min_free_bytes=args.min_free_gib * 1024**3)
    root = storage.check_storage(policy)
    library = Path.home() / '.local/lib/mastermind/worktree-storage/worktree_storage.py'
    configs = sorted((Path.home() / 'Library/Application Support').glob('Claude*/claude_desktop_config.json'))
    cli = Path.home() / '.claude/settings.json'
    codex = Path.home() / '.codex/hooks.json'
    print(json.dumps(dict(mode='apply' if args.apply else 'report', root=str(root), helper=str(library),
                         claude_profiles=[str(p.parent.name) for p in configs], cli_settings=str(cli))))
    if not args.apply:
        return
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup = root / 'backups' / ('storage-install-' + stamp)
    changes = []
    originals = {}
    for path in configs:
        originals[path] = path.read_bytes()
        prefs = json.loads(originals[path]).get('preferences', {})
        changes.append(dict(path=str(path), key='preferences.chillingSlothLocation',
                            before=dict(present='chillingSlothLocation' in prefs, value=prefs.get('chillingSlothLocation'))))
    originals[cli] = cli.read_bytes() if cli.exists() else None
    original_cli = json.loads(originals[cli]) if originals[cli] else {}
    originals[codex] = codex.read_bytes() if codex.exists() else None
    original_codex = json.loads(originals[codex]) if originals[codex] else {}
    start_command = f'python3 "{library}" session-start'
    # Reconcile BOTH clients before the first helper/policy/settings write.
    cli_config = reconcile_session_start(original_cli, start_command)
    codex_config = reconcile_session_start(original_codex, start_command, codex=True)
    command = f'python3 "{library}" create'
    old_create = original_cli.get('hooks', {}).get('WorktreeCreate', [])
    if not args.without_create_hook and old_create and not all(h.get('command') == command for group in old_create for h in group.get('hooks', [])):
        raise RuntimeError('existing global WorktreeCreate needs reconciliation; not replaced')
    changes.append(dict(path=str(cli), key='hooks', before=original_cli.get('hooks')))
    changes.append(dict(path=str(codex), key='hooks', before=original_codex.get('hooks')))
    instructions = (
        '\n<!-- mastermind-external-worktree-storage -->\n'
        '## External SSD worktree placement\n\n'
        'New local agent worktrees must use the external volume in '
        '`~/.config/mastermind/worktree-storage.json`. Use '
        '`python3 ~/.local/lib/mastermind/worktree-storage/worktree_storage.py create` '
        'with JSON stdin containing the existing repository `cwd`, a safe `name`, '
        'and the actual current `session_id`. Use the printed absolute path. '
        'Never fall back to internal disk or create a replacement mount directory '
        'when the SSD is unavailable. Codex native Worktree root and Claude Desktop '
        'Worktree location must use their client directories under that policy root. '
        'Preserve existing active worktrees and shared Git stores; this changes new '
        'placement only. Preserve repository branch/review/cleanup rules and sparse '
        'defaults. A native setting alone does not override a legacy creation hook.\n'
        '<!-- /mastermind-external-worktree-storage -->\n'
    ).encode()
    instruction_paths = [Path.home() / '.codex/AGENTS.md', Path.home() / '.claude/CLAUDE.md']
    for path in instruction_paths:
        originals[path] = path.read_bytes() if path.exists() else None
        if b'<!-- mastermind-external-worktree-storage -->' in (originals[path] or b'') and instructions not in originals[path]:
            raise RuntimeError(f'existing storage instructions need reconciliation: {path}')
        changes.append(dict(path=str(path), key='appended_instruction_block',
                            before=dict(present=path.exists(), already_present=instructions in (originals[path] or b'')),
                            installed_block=instructions.decode()))
    storage.prepare_root(policy)
    backup.mkdir(parents=True, exist_ok=False)
    receipt_path = backup / 'receipt.json'
    receipt_path.write_text(json.dumps(dict(status='PREPARED', installed_at=stamp, changes=changes,
        helper_previously_present=library.exists(), policy_previously_present=storage.POLICY_PATH.exists()), indent=2)+'\n')
    if library.exists():
        (backup / 'previous-helper.py').write_bytes(library.read_bytes())
    source = Path(__file__).with_name('worktree_storage.py').read_bytes()
    write_if_unchanged(library, library.read_bytes() if library.exists() else None, source)
    policy_path = storage.POLICY_PATH
    previous = policy_path.read_bytes() if policy_path.exists() else None
    if previous is not None:
        (backup / 'previous-policy.json').write_bytes(previous)
    write_if_unchanged(policy_path, previous, (json.dumps(policy, indent=2)+'\n').encode())
    for path in configs:
        before = originals[path]
        config = json.loads(before)
        prefs = config.setdefault('preferences', {})
        wanted = dict(customPath=str(root / 'claude'))
        if prefs.get('chillingSlothLocation') != wanted:
            prefs['chillingSlothLocation'] = wanted
            write_if_unchanged(path, before, (json.dumps(config, indent=2)+'\n').encode())
        assert json.loads(path.read_text())['preferences']['chillingSlothLocation'] == wanted
    before = originals[cli]
    config = cli_config
    hooks = config.setdefault('hooks', {})
    # Preserve other hooks. There was no global WorktreeCreate on the audited
    # host; refuse unfamiliar creation wiring instead of restoring duplicates.
    command = f'python3 "{library}" create'
    old = hooks.get('WorktreeCreate', [])
    if not args.without_create_hook and old and not all(h.get('command') == command for group in old for h in group.get('hooks', [])):
        raise RuntimeError('existing global WorktreeCreate needs reconciliation; not replaced')
    if not args.without_create_hook:
        hooks['WorktreeCreate'] = [dict(hooks=[dict(type='command', command=command, timeout=300)])]
    write_if_unchanged(cli, before, (json.dumps(config, indent=2)+'\n').encode())
    # The user hook covers all Codex projects, including old source snapshots.
    # Trust remains an explicit native Codex step; never edit its trust store.
    write_if_unchanged(codex, originals[codex], (json.dumps(codex_config, indent=2)+'\n').encode())
    for path in instruction_paths:
        before = originals[path]
        if instructions not in (before or b''):
            write_if_unchanged(path, before, (before or b'') + instructions)
    receipt = json.loads(receipt_path.read_text())
    receipt.update(status='APPLIED', helper_sha256=hashlib.sha256(source).hexdigest(), policy=policy,
                   creation_hook='DEFERRED' if args.without_create_hook else 'INSTALLED',
                   codex_hook_trust='REVIEW_REQUIRED: trust the exact new SessionStart hook via /hooks',
                   codex_root='USER_ACTION_REQUIRED: Settings > Worktrees > Worktree root')
    receipt_path = backup / 'receipt.json'
    receipt_path.write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(dict(installed=True, receipt=str(receipt_path), helper_sha256=receipt['helper_sha256'],
                         profiles_verified=len(configs), active_app_reload='Verify UI or next session; no apps restarted')))


if __name__ == '__main__':
    main()
