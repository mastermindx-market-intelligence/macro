#!/usr/bin/env python3
"""Host-scoped external worktree storage. No scheduler or workload admission policy.

The optional host file is ~/.config/mastermind/worktree-storage.json. An installed
policy is mandatory: invalid/unavailable storage never falls back to local disk.
Git remains the worktree registry; receipts only identify repeat hook invocations.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import stat
import subprocess
import sys
import uuid

POLICY_PATH = Path.home() / '.config/mastermind/worktree-storage.json'
LOCK_REASON = 'mastermind-external-storage: removable volume protection'


class StorageError(RuntimeError):
    pass


def load_policy(path: Path | None = None) -> dict | None:
    path = Path(path or POLICY_PATH)
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text())
        if value['version'] != 1 or not isinstance(value['volume_uuid'], str) or not value['volume_uuid']:
            raise ValueError('invalid version or volume identity')
        for key in ('mount_point', 'root'):
            if not isinstance(value[key], str) or not Path(value[key]).is_absolute():
                raise ValueError(f'{key} must be absolute')
        floor = value['min_free_bytes']
        if not isinstance(floor, int) or isinstance(floor, bool) or floor < 0:
            raise ValueError('invalid free-space floor')
        return value
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise StorageError(f'invalid storage policy: {path}: {exc}') from exc


def volume_info(mount: Path) -> dict:
    try:
        result = subprocess.run(['diskutil', 'info', '-plist', str(mount)], capture_output=True, check=True, timeout=15)
        return plistlib.loads(result.stdout)
    except (OSError, subprocess.SubprocessError, plistlib.InvalidFileException) as exc:
        raise StorageError('SSD volume identity is unavailable') from exc


def _contained(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def client_roots(policy: dict) -> tuple[Path, ...]:
    return tuple(Path(policy['root']) / client for client in ('claude', 'codex', 'manual'))


def is_managed_worktree_path(policy: dict, path: Path) -> bool:
    """Audit, backup and other directories are not client session roots."""
    return any(root in Path(path).parents for root in client_roots(policy))


def _supported_filesystem(info: dict) -> bool:
    """Admit APFS or positively identified journaled HFS+, never plain `hfs`."""
    if info.get('FilesystemType') == 'apfs':
        return (info.get('FilesystemName', 'APFS') in ('APFS', 'Case-sensitive APFS')
                and info.get('Journaled', False) is False
                and 'JournalOffset' not in info and 'JournalSize' not in info)
    if info.get('FilesystemType') != 'hfs':
        return False
    # diskutil may omit Journaled; its canonical name and journal extent must
    # still agree. A display label alone is not evidence of an active journal.
    return (info.get('FilesystemName') in ('Journaled HFS+', 'Case-sensitive Journaled HFS+')
            and info.get('Journaled', True) is True
            and all(type(info.get(key)) is int and info[key] > 0
                    for key in ('JournalOffset', 'JournalSize')))


def check_storage(policy: dict, target: Path | None = None, *, check_space: bool = True) -> Path:
    mount, root = Path(policy['mount_point']), Path(policy['root'])
    target = Path(target or root)
    for item in (mount, root, target):
        if not item.is_absolute() or '..' in item.parts or item.resolve() != item:
            raise StorageError(f'unsafe storage path or symlink: {item}')
    if root == mount or not _contained(root, mount) or not _contained(target, root):
        raise StorageError('destination escapes the configured SSD workspace root')
    if not mount.is_dir():
        raise StorageError('SSD mount is unavailable; refusing internal fallback')
    info = volume_info(mount)
    if (info.get('VolumeUUID') != policy['volume_uuid'] or info.get('MountPoint') != str(mount)
            or info.get('Internal') is not False or info.get('Writable') is not True
            or not _supported_filesystem(info)):
        raise StorageError('SSD identity, mount, filesystem or writeability check failed')
    ancestor = target
    while not ancestor.exists():
        ancestor = ancestor.parent
    if ancestor.stat().st_dev != mount.stat().st_dev:
        raise StorageError('destination is on another filesystem')
    if check_space and shutil.disk_usage(mount).free < policy['min_free_bytes']:
        raise StorageError('SSD free space is below the storage policy floor')
    return root


def _mkdir_on_volume(policy: dict, target: Path) -> None:
    """Walk using directory descriptors: never follow a replaced path component."""
    check_storage(policy, target)
    mount = Path(policy['mount_point'])
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open(mount, flags)
    try:
        device = os.fstat(fd).st_dev
        for part in target.relative_to(mount).parts:
            try:
                os.mkdir(part, mode=0o700, dir_fd=fd)
            except FileExistsError:
                pass
            child = os.open(part, flags, dir_fd=fd)
            if os.fstat(child).st_dev != device:
                os.close(child)
                raise StorageError('workspace component crosses filesystems')
            os.close(fd)
            fd = child
    finally:
        os.close(fd)
    check_storage(policy, target)


def prepare_root(policy: dict) -> Path:
    root = check_storage(policy)
    _mkdir_on_volume(policy, root)
    return root


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(['git', '-c', 'maintenance.auto=false', '-c', 'gc.auto=0', '-C', str(repo), *args],
                            text=True, capture_output=True)
    if result.returncode:
        raise StorageError(f'git {args[0]} failed: {result.stderr.strip()[-1000:]}')
    return result.stdout.strip()


def destination(policy: dict, repo: Path, name: str, session: str) -> tuple[Path, str]:
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,99}', name):
        raise StorageError('unsafe worktree name')
    if not session:
        raise StorageError('session identity is required')
    common = git(repo, 'rev-parse', '--path-format=absolute', '--git-common-dir')
    key = hashlib.sha256((common + '\0' + session + '\0' + name).encode()).hexdigest()
    repo_key = hashlib.sha256(common.encode()).hexdigest()[:16]
    return Path(policy['root']) / 'claude' / repo_key / f'{name}-{key[:16]}', key


def _default_base(repo: Path) -> tuple[str, bool]:
    try:
        git(repo, 'remote', 'get-url', 'origin')
    except StorageError:
        return 'HEAD', False
    try:
        ref = git(repo, 'symbolic-ref', 'refs/remotes/origin/HEAD')
        return ref.removeprefix('refs/remotes/origin/'), True
    except StorageError:
        for branch in ('main', 'master'):
            try:
                git(repo, 'show-ref', '--verify', f'refs/remotes/origin/{branch}')
                return branch, True
            except StorageError:
                pass
    raise StorageError('origin default branch is unknown; refusing a stale-base fallback')


def create_worktree(policy: dict, repo: Path, name: str, session: str, *, base: str | None = None, fetch: bool = True) -> Path:
    repo = Path(repo).resolve()
    root = prepare_root(policy)
    dest, key = destination(policy, repo, name, session)
    common = git(repo, 'rev-parse', '--path-format=absolute', '--git-common-dir')
    repo_key = hashlib.sha256(common.encode()).hexdigest()[:16]
    lock_dir, receipt_dir = root / '.storage-locks', root / '.storage-receipts'
    _mkdir_on_volume(policy, lock_dir)
    _mkdir_on_volume(policy, receipt_dir)
    # Serialization only for this repository's short Git metadata transaction.
    # It is not a limit on running agents, builds, or host concurrency.
    fd = os.open(lock_dir / (repo_key + '.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        check_storage(policy, dest)
        receipt = receipt_dir / (key + '.json')
        branch = f'claude/ssd-{name}-{key[:16]}'
        expected = dict(key=key, common=common, path=str(dest), branch=branch)
        if dest.exists():
            try:
                if receipt.is_symlink() or json.loads(receipt.read_text()) != expected:
                    raise ValueError('receipt mismatch')
            except (OSError, ValueError):
                raise StorageError(f'unreceipted or foreign destination retained: {dest}') from None
            registered = git(repo, 'worktree', 'list', '--porcelain').splitlines()
            if (f'worktree {dest}' not in registered or git(dest, 'rev-parse', '--path-format=absolute', '--git-common-dir') != common
                    or git(dest, 'symbolic-ref', '--short', 'HEAD') != branch):
                raise StorageError('existing worktree identity changed; refusing adoption')
            return dest
        if receipt.exists():
            raise StorageError('receipted worktree is missing; refusing replacement')
        if base is None:
            base, fetch = _default_base(repo)
        if fetch:
            if re.fullmatch(r'pr-[0-9]+', name):
                base_ref = f'refs/mastermind-worktrees/base/{key}'
                git(repo, 'fetch', 'origin', f'+refs/pull/{name[3:]}/head:{base_ref}')
            else:
                remote_branch = base.removeprefix('refs/remotes/origin/').removeprefix('origin/')
                base_ref = f'refs/mastermind-worktrees/base/{key}'
                git(repo, 'fetch', 'origin', f'+refs/heads/{remote_branch}:{base_ref}')
        else:
            base_ref = base
        # A transaction-specific ref prevents unrelated fetches from changing the base.
        commit = git(repo, 'rev-parse', '--verify', base_ref + '^{commit}')
        _mkdir_on_volume(policy, dest.parent)
        git(repo, 'worktree', 'add', '--lock', '--reason', LOCK_REASON, '--no-checkout', '--no-track', '-b', branch, str(dest), commit)
        try:
            profile_path = repo / 'config/sparse_worktree.json'
            if profile_path.exists():
                profile = json.loads(profile_path.read_text())
                if profile.get('enabled'):
                    dirs = git(repo, 'ls-tree', '-d', '--name-only', commit).splitlines()
                    selected = [p for p in dirs if p not in profile.get('exclude_dirs', [])]
                    git(dest, 'sparse-checkout', 'set', '--cone', '--', *selected)
            git(dest, 'read-tree', '-mu', 'HEAD')
            check_storage(policy, dest)
            with receipt.open('x') as out:
                json.dump(expected, out, sort_keys=True)
                out.write('\n')
        except Exception as exc:
            # Preserve failed partial work and its lock. Never force-delete a
            # directory that another actor might already have entered.
            raise StorageError(f'creation incomplete; locked worktree preserved at {dest}: {exc}') from exc
        return dest



# Immutable-local mode is separate from ordinary create. Its per-Git timeout and
# cooperative flock are not a transaction deadline or descendant-drain guarantee.
# Partial/unknown effects are retained; this helper never rolls them back.
def _immutable_git(repo: Path, *args: str, input: bytes | None = None,
                   allowed: tuple[int, ...] = (0,)) -> bytes:
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1', GIT_ALLOW_PROTOCOL='',
               GIT_NO_REPLACE_OBJECTS='1', GIT_GRAFT_FILE=os.devnull,
               GIT_TERMINAL_PROMPT='0')
    argv = ['git', '--no-optional-locks', '--literal-pathspecs', '-c',
            'protocol.allow=never', '-c', 'maintenance.auto=false', '-c', 'gc.auto=0',
            '-c', 'core.fsmonitor=false', '-c', 'core.quotePath=false', '-C', str(repo), *args]
    try:
        result = subprocess.run(argv, input=input, capture_output=True, env=env, timeout=20)
    except subprocess.TimeoutExpired as exc:
        raise StorageError('immutable-local Git timed out; any partial effect is retained, not retried') from exc
    if result.returncode not in allowed:
        raise StorageError(f'immutable-local git {args[0]} refused (exit {result.returncode})')
    return result.stdout


def _immutable_path(raw: bytes) -> str:
    """Explicit subset: UTF-8, no control characters, backslash, double quote or edge spaces."""
    try:
        value = raw.decode('utf-8', 'strict')
    except UnicodeDecodeError as exc:
        raise StorageError('immutable-local refuses non-UTF8 pathnames') from exc
    if (not value or any(ord(c) < 32 or 127 <= ord(c) <= 159 or c == '\\' for c in value)
            or '"' in value or any(p in ('.', '..') or p != p.strip(' ') for p in value.split('/'))):
        raise StorageError('immutable-local refuses unsupported pathname characters')
    return value


def _immutable_git_path(repo: Path, *args: str) -> Path:
    raw = _immutable_git(repo, 'rev-parse', '--path-format=absolute', *args)
    return Path(_immutable_path(raw.removesuffix(b'\n')))


def _immutable_snapshot(path: Path) -> dict:
    if path.is_symlink():
        raise StorageError('immutable-local refuses symlinked attribute/config input')
    if not path.exists():
        return dict(path=str(path), sha256=None)
    if not path.is_file():
        raise StorageError('immutable-local attribute/config input is not a regular file')
    return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def _immutable_controls(repo: Path) -> dict:
    """Capture actual config/global/info inputs without displaying driver commands."""
    raw = _immutable_git(repo, 'config', '--null', '--list', '--show-origin')
    fields = raw.split(b'\0')
    if fields[-1:] != [b''] or len(fields[:-1]) % 2:
        raise StorageError('unrecognized Git configuration output')
    configs, settings = {}, {}
    for i in range(0, len(fields) - 1, 2):
        origin, entry = fields[i:i + 2]
        key, _, value = entry.partition(b'\n')
        if key == b'core.hookspath':
            raise StorageError('immutable-local refuses custom hooksPath configuration')
        settings[key] = value
        if origin.startswith(b'file:'):
            path = Path(_immutable_path(origin[5:])).expanduser()
            if not path.is_absolute():
                path = repo / path
            configs[str(path)] = _immutable_snapshot(path)
    hooks = _immutable_git_path(repo, '--git-path', 'hooks')
    if any(os.access(hooks / name, os.X_OK)
           for name in ('post-checkout', 'post-index-change', 'reference-transaction')):
        raise StorageError('immutable-local refuses executable checkout/index/reference hooks')
    variables = _immutable_git(repo, 'var', '-l')
    attrs = {}
    for line in variables.split(b'\n'):
        key, _, value = line.partition(b'=')
        if key in (b'GIT_ATTR_SYSTEM', b'GIT_ATTR_GLOBAL'):
            path = Path(_immutable_path(value))
            attrs[key.decode('ascii')] = _immutable_snapshot(path)
    if set(attrs) != {'GIT_ATTR_SYSTEM', 'GIT_ATTR_GLOBAL'}:
        raise StorageError('Git cannot identify effective system/global attribute sources')
    info = _immutable_git_path(repo, '--git-path', 'info/attributes')
    attrs['info'] = _immutable_snapshot(info)
    return dict(config_sha256=hashlib.sha256(raw).hexdigest(),
                config_sources=sorted(configs.values(), key=lambda x: x['path']),
                attribute_sources=attrs)


def _immutable_attributes(repo: Path, paths: list[str], commit: str | None = None) -> dict:
    before = _immutable_controls(repo)
    working = {}
    if commit is None:
        # Include absent ancestors: a newly added, untracked .gitattributes can
        # affect status without altering the commit, index tree or source repo.
        for name in paths:
            parent = Path(name).parent
            while True:
                candidate = repo / parent / '.gitattributes'
                working[str(candidate)] = _immutable_snapshot(candidate)
                if parent == Path('.'):
                    break
                parent = parent.parent
    stdin = b''.join(p.encode('utf-8') + b'\0' for p in paths)
    source = ['--source=' + commit] if commit else []
    raw = _immutable_git(repo, 'check-attr', *source, '--stdin', '-z', 'filter', input=stdin)
    fields = raw.split(b'\0')
    if fields[-1:] != [b''] or len(fields[:-1]) != len(paths) * 3:
        raise StorageError('unrecognized source-aware Git attribute output')
    for i, name in enumerate(paths):
        path, attribute, value = fields[i * 3:i * 3 + 3]
        if path != name.encode('utf-8') or attribute != b'filter':
            raise StorageError('Git attribute pathname identity changed')
        if value not in (b'unspecified', b'unset'):
            raise StorageError('immutable-local materialized path selects a filter')
    if _immutable_controls(repo) != before:
        raise StorageError('attribute/config input changed during inspection')
    if any(_immutable_snapshot(Path(p)) != value for p, value in working.items()):
        raise StorageError('worktree attributes changed during inspection')
    return dict(controls=before, working_attributes=sorted(working.values(), key=lambda x: x['path']),
                filter_sha256=hashlib.sha256(raw).hexdigest())


def _immutable_plan(repo: Path, commit: str) -> dict:
    help_text = _immutable_git(repo, 'check-attr', '-h', allowed=(0, 129))
    if any(option not in help_text for option in (b'--source', b'--stdin', b'-z')):
        raise StorageError('Git lacks source-aware NUL-delimited attribute inspection')
    if _immutable_git(repo, 'cat-file', '-t', commit) != b'commit\n':
        raise StorageError('immutable-local requires an existing local commit object')
    tree = _immutable_git(repo, 'rev-parse', '--verify', commit + '^{tree}').decode('ascii').strip()
    raw = _immutable_git(repo, 'ls-tree', '-r', '-t', '-z', commit)
    entries, index_entries = [], {}
    for row in raw.split(b'\0'):
        if row:
            meta, name = row.split(b'\t', 1)
            mode, kind, oid = meta.split()
            if name.split(b'/')[-1] == b'.gitattributes' and mode not in (b'100644', b'100755'):
                raise StorageError('immutable-local attribute source is not a regular committed file')
            entries.append((kind, oid.decode('ascii'), _immutable_path(name)))
            if kind != b'tree':
                index_entries[name] = (mode, oid, b'0')
    profile_entry = [x for x in entries if x[2] == 'config/sparse_worktree.json']
    profile = None
    if profile_entry:
        if len(profile_entry) != 1 or profile_entry[0][0] != b'blob':
            raise StorageError('immutable sparse profile is not a blob')
        profile = json.loads(_immutable_git(repo, 'cat-file', 'blob', profile_entry[0][1]))
        if not isinstance(profile, dict) or not isinstance(profile.get('enabled', False), bool):
            raise StorageError('invalid immutable sparse profile')
    sparse = bool(profile and profile.get('enabled'))
    excluded = profile.get('exclude_dirs', []) if sparse else []
    if not isinstance(excluded, list) or any(not isinstance(x, str) for x in excluded):
        raise StorageError('invalid immutable sparse exclusions')
    selected = sorted(name for kind, oid, name in entries
                      if kind == b'tree' and '/' not in name and name not in excluded)
    materialized = [x for x in entries if x[0] != b'tree'
                    and (not sparse or '/' not in x[2] or x[2].split('/', 1)[0] in selected)]
    if any(kind != b'blob' for kind, oid, name in materialized):
        raise StorageError('immutable-local does not initialize submodule/gitlink paths')
    paths = [name for kind, oid, name in materialized]
    objects = sorted({oid for kind, oid, name in materialized})
    if objects:
        actual = _immutable_git(repo, 'cat-file', '--batch-check=%(objectname) %(objecttype)',
                                input=('\n'.join(objects) + '\n').encode()).splitlines()
        if actual != [(oid + ' blob').encode() for oid in objects]:
            raise StorageError('required checkout blobs are not all local; refusing fetch')
    if sparse and _immutable_git(repo, 'config', '--bool', '--get', 'extensions.worktreeConfig',
                                  allowed=(0, 1)) != b'true\n':
        raise StorageError('sparse worktree config isolation must already be enabled')
    attributes = _immutable_attributes(repo, paths, commit)
    return dict(tree=tree, sparse=sparse, selected=selected, paths=paths, index_entries=index_entries,
                excluded_paths=[name for kind, oid, name in entries if kind != b'tree' and name not in paths],
                profile_oid=profile_entry[0][1] if profile_entry else None,
                attributes=attributes)


def _immutable_index_guard(repo: Path, plan: dict) -> None:
    """Read index metadata only; do not refresh it or run content conversions."""
    # Without --sparse, ls-files expands sparse directory entries in memory.
    # -v exposes assume-unchanged as lowercase and skip-worktree as S.
    raw = _immutable_git(repo, 'ls-files', '--stage', '-v', '-z', '--full-name')
    actual, flags = {}, {}
    for row in raw.split(b'\0'):
        if not row:
            continue
        try:
            metadata, name = row.split(b'\t', 1)
            flag, mode, oid, stage = metadata.split()
        except ValueError as exc:
            raise StorageError('unrecognized immutable-local index output') from exc
        if name in actual or stage != b'0':
            raise StorageError('immutable-local index does not match immutable tree; retained')
        actual[name], flags[name] = (mode, oid, stage), flag
    if actual != plan['index_entries']:
        raise StorageError('immutable-local index does not match immutable tree; retained')
    required = {name.encode('utf-8') for name in plan['paths']}
    for name, flag in flags.items():
        if name in required:
            if flag != b'H':
                raise StorageError('immutable-local required materialized path has index flags; retained')
        elif flag != b'S':
            raise StorageError('immutable-local excluded path has unexpected index flags; retained')


def _immutable_sparse_state(repo: Path, plan: dict) -> dict:
    if any(not os.path.lexists(repo / name) for name in plan['paths']):
        raise StorageError('immutable-local required materialized path is absent; retained')
    if any(os.path.lexists(repo / name) for name in plan['excluded_paths']):
        raise StorageError('immutable-local excluded tracked path is present; retained')
    values = {}
    for key in ('core.sparseCheckout', 'core.sparseCheckoutCone', 'index.sparse'):
        raw = _immutable_git(repo, 'config', '--bool', '--get', key, allowed=(0, 1))
        if raw not in (b'', b'true\n', b'false\n'):
            raise StorageError('invalid effective sparse configuration')
        values[key] = raw == b'true\n'
    if values['core.sparseCheckout'] != plan['sparse']:
        raise StorageError('immutable-local sparse mode changed')
    if plan['sparse']:
        if not values['core.sparseCheckoutCone']:
            raise StorageError('immutable-local sparse cone mode changed')
        actual = _immutable_git(repo, 'sparse-checkout', 'list')
        listed = [_immutable_path(p) for p in actual.split(b'\n') if p]
        if sorted(listed) != plan['selected']:
            raise StorageError('immutable-local sparse selection changed')
    pattern_path = _immutable_git_path(repo, '--git-path', 'info/sparse-checkout')
    return dict(settings=values, patterns=_immutable_snapshot(pattern_path))


def _immutable_registered(repo: Path, dest: Path, common: Path, commit: str) -> bool:
    if _immutable_git_path(dest, '--git-common-dir') != common:
        return False
    records = _immutable_git(repo, 'worktree', 'list', '--porcelain', '-z').split(b'\0\0')
    for record in records:
        fields = record.split(b'\0')
        if b'worktree ' + str(dest).encode() in fields:
            return (b'HEAD ' + commit.encode() in fields and b'detached' in fields
                    and b'locked ' + LOCK_REASON.encode() in fields
                    and not any(x.startswith((b'branch ', b'prunable')) for x in fields))
    return False


def _immutable_fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _immutable_write_receipt(path: Path, value: dict) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as out:
        json.dump(value, out, sort_keys=True)
        out.write('\n')
        out.flush()
        os.fsync(out.fileno())
    _immutable_fsync_directory(path.parent)


def create_immutable_local(policy: dict, repo: Path, name: str, session: str, commit: str) -> Path:
    if (not isinstance(commit, str) or not re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', commit)
            or not isinstance(session, str) or not session.strip()
            or not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,99}', name)):
        raise StorageError('immutable-local requires a full commit OID, safe name and actual session_id')
    repo = Path(repo)
    if not repo.is_absolute():
        raise StorageError('immutable-local cwd must be absolute')
    _immutable_path(os.fsencode(repo))
    repo = repo.resolve(strict=True)
    check_storage(policy)
    plan = _immutable_plan(repo, commit)
    common = _immutable_git_path(repo, '--git-common-dir')
    key = hashlib.sha256((str(common) + '\0' + session + '\0' + name
                          + '\0immutable-local\0' + commit).encode()).hexdigest()
    repo_key = hashlib.sha256(str(common).encode()).hexdigest()[:16]
    root = prepare_root(policy)
    dest = root / 'claude' / repo_key / f'{name}-{key[:16]}'
    lock_dir, receipt_dir = root / '.storage-locks', root / '.storage-receipts'
    _mkdir_on_volume(policy, lock_dir)
    _mkdir_on_volume(policy, receipt_dir)
    lock_fd = os.open(lock_dir / (repo_key + '.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(lock_fd, 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        check_storage(policy, dest)
        stable = dict(version=2, mode='immutable-local', key=key, common=str(common),
                      path=str(dest), branch=None, commit=commit, tree=plan['tree'],
                      session_sha256=hashlib.sha256(session.encode()).hexdigest(),
                      sparse=plan['sparse'], selected=plan['selected'], profile_oid=plan['profile_oid'],
                      paths_sha256=hashlib.sha256(b''.join(p.encode() + b'\0' for p in plan['paths'])).hexdigest())
        receipt = receipt_dir / (key + '.json')
        if dest.exists():
            try:
                if receipt.is_symlink():
                    raise ValueError('symlink')
                saved = json.loads(receipt.read_text())
                if (set(saved) != set(stable) | {'state', 'attributes', 'materialization'}
                        or any(saved[k] != v for k, v in stable.items()) or saved['state'] != 'COMPLETE'):
                    raise ValueError('receipt mismatch')
            except (OSError, TypeError, ValueError):
                raise StorageError(f'unreceipted or foreign destination retained: {dest}') from None
            if not _immutable_registered(repo, dest, common, commit):
                raise StorageError('immutable-local destination identity changed; retained')
            # Attribute and exact index checks must precede status: status itself
            # may execute a filter selected by an unexpected staged path.
            attributes = _immutable_attributes(dest, plan['paths'])
            materialization = _immutable_sparse_state(dest, plan)
            if attributes != saved['attributes'] or materialization != saved['materialization']:
                raise StorageError('immutable-local attribute/config/sparse drift; retained without repair')
            _immutable_index_guard(dest, plan)
            if _immutable_git(dest, 'status', '--porcelain=v1', '--untracked-files=all'):
                raise StorageError('immutable-local destination is dirty; retained without adoption')
            return dest
        if os.path.lexists(receipt):
            raise StorageError('receipted worktree is missing; refusing replacement')
        if _immutable_plan(repo, commit) != plan:
            raise StorageError('immutable-local preflight changed before creation')
        _mkdir_on_volume(policy, dest.parent)
        pending = dict(stable, state='PREPARING')
        _immutable_write_receipt(receipt, pending)
        try:
            _immutable_git(repo, 'worktree', 'add', '--lock', '--reason', LOCK_REASON,
                           '--no-checkout', '--detach', str(dest), commit)
            # Destination-specific config (including conditional includes) may differ.
            _immutable_attributes(dest, plan['paths'], commit)
            if plan['sparse']:
                _immutable_git(dest, 'sparse-checkout', 'set', '--cone', '--', *plan['selected'])
            _immutable_git(dest, 'read-tree', '-mu', 'HEAD')
            check_storage(policy, dest)
            if not _immutable_registered(repo, dest, common, commit):
                raise StorageError('immutable-local creation identity postcondition failed')
            attributes = _immutable_attributes(dest, plan['paths'])
            materialization = _immutable_sparse_state(dest, plan)
            _immutable_index_guard(dest, plan)
            if _immutable_git(dest, 'status', '--porcelain=v1', '--untracked-files=all'):
                raise StorageError('immutable-local created worktree is dirty')
            if receipt.is_symlink() or json.loads(receipt.read_text()) != pending:
                raise StorageError('pending receipt changed; partial state retained')
            complete = dict(stable, state='COMPLETE', attributes=attributes, materialization=materialization)
            temp = receipt.with_name(receipt.name + '.' + uuid.uuid4().hex + '.tmp')
            _immutable_write_receipt(temp, complete)
            os.replace(temp, receipt)
            _immutable_fsync_directory(receipt_dir)
        except Exception as exc:
            # File and receipt-directory fsync request metadata settlement. They do
            # not establish universal power-loss durability across hardware/Git stores.
            raise StorageError(f'creation incomplete; partial state and any lock retained at {dest}: {exc}') from exc
        return dest


def _preservation_git(cwd: Path, *args: str, input_bytes: bytes | None = None) -> bytes | None:
    """Read index/status facts without optional refresh, fsmonitor or lazy fetch."""
    try:
        result = subprocess.run(
            ['git', '--no-optional-locks', '-c', 'core.fsmonitor=false', '-C', str(cwd), *args],
            input=input_bytes, capture_output=True, timeout=20,
            env=dict(os.environ, GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1'))
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout if result.returncode == 0 else None


def materialized_index_safe(cwd: Path, *, allow_sparse: bool = False) -> bool | None:
    """False preserves hidden work; None preserves an index we cannot inspect.

    An uppercase S entry is admissible only when it is absent through regular
    directory ancestors AND Git's current sparse rules positively exclude it.
    A present S entry, assume-unchanged flag or conflict is never clean proof.
    This is read-only: never reset flags or ask status to refresh them away.
    """
    raw = _preservation_git(cwd, 'ls-files', '-v', '--stage', '-z')
    if raw is None or (raw and not raw.endswith(b'\0')):
        return None
    absent = []
    for record in raw.split(b'\0'):
        if not record:
            continue
        try:
            header, name = record.split(b'\t', 1)
            flag, mode, oid, stage = header.split()
        except ValueError:
            return None
        if (mode not in (b'100644', b'100755', b'120000', b'160000')
                or len(oid) not in (40, 64) or re.fullmatch(b'[0-9a-f]+', oid) is None
                or not name or any(p in (b'', b'.', b'..') for p in name.split(b'/'))):
            return None
        if stage != b'0' or flag not in (b'H', b'S'):
            return False
        if flag == b'H':
            continue
        if not allow_sparse:
            return False
        # lexists() would turn permission errors into false absence. Inspect
        # ancestors too, so a dangling/replaced symlink is not sparse absence.
        cursor = Path(cwd)
        for part in name.split(b'/'):
            cursor = cursor / os.fsdecode(part)
            try:
                entry = cursor.lstat()
            except FileNotFoundError:
                absent.append(name)
                break
            except OSError:
                return None
            if not stat.S_ISDIR(entry.st_mode):
                return False
        else:
            return False  # even a directory materialized at the tracked path
    if absent:
        enabled = _preservation_git(cwd, 'config', '--bool', '--default=false',
                                    '--get', 'core.sparseCheckout')
        if enabled is None:
            return None
        if enabled.strip() != b'true':
            return False
        included = _preservation_git(cwd, 'sparse-checkout', 'check-rules', '-z',
                                     input_bytes=b'\0'.join(absent) + b'\0')
        if included is None or (included and not included.endswith(b'\0')):
            return None
        # A missing, manually skipped IN-cone file is a hidden deletion, not
        # a legitimate sparse omission. Unknown/unsupported rule reads refuse.
        if included:
            return False
    return True


def protect_worktree(policy: dict, cwd: Path, *, sparsify: bool = True) -> bool:
    """Protect a newly opened external linked checkout; grandfather internal ones."""
    cwd = Path(cwd).resolve()
    if not is_managed_worktree_path(policy, cwd):
        return False
    check_storage(policy, cwd)
    common = git(cwd, 'rev-parse', '--path-format=absolute', '--git-common-dir')
    gitdir = git(cwd, 'rev-parse', '--path-format=absolute', '--git-dir')
    if common == gitdir:
        return False
    # Preserve all pre-existing lock reasons, including operator holds.
    lock = Path(gitdir) / 'locked'
    if not lock.exists():
        git(cwd, 'worktree', 'lock', '--reason', LOCK_REASON, str(cwd))
    profile = cwd / 'config/sparse_worktree.json'
    if not sparsify or not profile.exists():
        return True
    sparse = _preservation_git(cwd, 'config', '--bool', '--default=false',
                               '--get', 'core.sparseCheckout')
    if sparse is None or sparse.strip() not in (b'true', b'false'):
        raise StorageError('could not inspect worktree sparse configuration')
    if sparse.strip() == b'true':
        return True
    config = json.loads(profile.read_text())
    if not config.get('enabled'):
        return True
    safe = materialized_index_safe(cwd)
    if safe is None:
        raise StorageError('could not inspect worktree index; sparse conversion refused')
    if not safe:
        return True
    dirty = _preservation_git(cwd, 'status', '--porcelain=v1', '-z',
                              '--untracked-files=all', '--ignore-submodules=none')
    if dirty is None:
        raise StorageError('could not inspect worktree status; sparse conversion refused')
    if not dirty:
        dirs = git(cwd, 'ls-tree', '-d', '--name-only', 'HEAD').splitlines()
        selected = [p for p in dirs if p not in config.get('exclude_dirs', [])]
        git(cwd, 'sparse-checkout', 'set', '--cone', '--', *selected)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path)
    parser.add_argument('command', choices=['check', 'create', 'create-immutable-local', 'check-path', 'session-start'])
    parser.add_argument('path', nargs='?', type=Path)
    args = parser.parse_args()
    try:
        policy = load_policy(args.config)
        if policy is None:
            raise StorageError('host storage policy is not installed')
        if args.command == 'session-start':
            payload = json.load(sys.stdin)
            protected = protect_worktree(policy, Path(payload['cwd']))
            print('External SSD worktree verified and protected.' if protected else 'Existing checkout retained. Create new worktrees through the required external SSD storage helper; no internal fallback.')
        elif args.command == 'create-immutable-local':
            payload = json.load(sys.stdin)
            if (not isinstance(payload, dict) or set(payload) != {'cwd', 'name', 'session_id', 'commit'}
                    or any(not isinstance(payload[k], str) or not payload[k].strip() for k in payload)):
                raise StorageError('immutable-local requires exactly cwd/name/session_id/commit strings')
            result = create_immutable_local(policy, Path(payload['cwd']), payload['name'],
                                            payload['session_id'], payload['commit'])
            print(result)
        elif args.command == 'create':
            payload = json.load(sys.stdin)
            result = create_worktree(policy, Path(payload['cwd']), payload['name'], payload.get('session_id') or str(uuid.uuid4()))
            print(result)
        else:
            root = check_storage(policy, args.path)
            print(json.dumps(dict(status='SSD_VERIFIED', root=str(root), volume_uuid=policy['volume_uuid'])))
        return 0
    except (StorageError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f'worktree-storage: REFUSED: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
