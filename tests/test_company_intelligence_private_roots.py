"""Private deployment boundary: unsafe inputs refuse before serving can start."""
from __future__ import annotations

import importlib.util
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
HELPER = REPO / 'app/deploy/company-intelligence-private-roots.py'
spec = importlib.util.spec_from_file_location('ci_private_roots', HELPER)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


@pytest.fixture
def parent(tmp_path):
    # An explicit test-only descriptor replaces the trusted production /var/lib.
    anchor = tmp_path / 'trusted'
    anchor.mkdir(mode=0o700)
    fd = os.open(anchor, helper.OPEN_DIRECTORY)
    try:
        yield anchor, fd
    finally:
        os.close(fd)


def provision(parent):
    helper._provision_at(parent[1], os.getuid(), os.getgid())


def private_path(parent, parts):
    return parent[0].joinpath(*parts)


def test_create_only_empty_exact_private_directories_and_preserve_rerun(parent):
    provision(parent)
    expected = {private_path(parent, parts) for parts in helper.PRIVATE_PATHS}
    assert set(parent[0].rglob('*')) == expected
    for path in expected:
        info = path.lstat()
        assert stat.S_ISDIR(info.st_mode)
        assert stat.S_IMODE(info.st_mode) == 0o700
        assert (info.st_uid, info.st_gid) == (os.getuid(), os.getgid())
    sentinel = parent[0] / helper.ROOT_NAME / 'publisher/source/existing.html'
    sentinel.write_bytes(b'preserve retained source bytes\x00')
    sentinel.chmod(0o600)
    before = sentinel.stat()
    provision(parent)
    after = sentinel.stat()
    assert sentinel.read_bytes() == b'preserve retained source bytes\x00'
    assert (before.st_ino, before.st_mtime_ns, before.st_mode) == (after.st_ino, after.st_mtime_ns, after.st_mode)
    assert not (parent[0] / helper.ROOT_NAME / 'state/current.json').exists()


@pytest.mark.parametrize('parts', helper.PRIVATE_PATHS)
@pytest.mark.parametrize('kind', ['symlink', 'dangling', 'file', 'mode'])
def test_each_unsafe_existing_slot_refuses_without_altering_it(parent, parts, kind):
    slot = private_path(parent, parts)
    slot.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    # mkdir(parents=True) may create intermediate dirs with a wider default.
    for path in parent[0].rglob('*'):
        if path.is_dir():
            path.chmod(0o700)
    target = parent[0] / 'unrelated-target'
    if kind == 'symlink':
        target.mkdir(mode=0o700)
        (target / 'sentinel').write_bytes(b'untouched')
        slot.symlink_to(target, target_is_directory=True)
    elif kind == 'dangling':
        slot.symlink_to(target, target_is_directory=True)
    elif kind == 'file':
        slot.write_bytes(b'do not replace')
    else:
        slot.mkdir(mode=0o750)
    before = slot.lstat()
    with pytest.raises(helper.ProvisioningError):
        provision(parent)
    after = slot.lstat()
    assert (before.st_ino, before.st_mode, before.st_mtime_ns) == (after.st_ino, after.st_mode, after.st_mtime_ns)
    if kind == 'symlink':
        assert (target / 'sentinel').read_bytes() == b'untouched'
        assert list(target.iterdir()) == [target / 'sentinel']
    elif kind == 'dangling':
        assert not target.exists()
    elif kind == 'file':
        assert slot.read_bytes() == b'do not replace'


@pytest.mark.parametrize('field', ['st_uid', 'st_gid'])
def test_wrong_owner_or_group_is_refused(parent, monkeypatch, field):
    provision(parent)
    target = (parent[0] / helper.ROOT_NAME / 'artifacts').stat().st_ino
    real = os.fstat
    def changed(fd):
        info = real(fd)
        if info.st_ino != target:
            return info
        values = list(info)
        values[4 if field == 'st_uid' else 5] += 1
        return os.stat_result(values)
    monkeypatch.setattr(os, 'fstat', changed)
    with pytest.raises(helper.ProvisioningError, match='owner or group'):
        provision(parent)


def test_bad_existing_sibling_refuses_before_creating_missing_nodes(parent):
    root = parent[0] / helper.ROOT_NAME
    root.mkdir(mode=0o700)
    (root / 'publisher').mkdir(mode=0o777)
    (root / 'publisher').chmod(0o777)
    with pytest.raises(helper.ProvisioningError):
        provision(parent)
    assert sorted(path.name for path in root.iterdir()) == ['publisher']
    assert stat.S_IMODE((root / 'publisher').stat().st_mode) == 0o777


@pytest.mark.parametrize('mode', [0o702, 0o720, 0o777])
def test_writable_parent_refuses_before_any_creation(parent, mode):
    parent[0].chmod(mode)
    with pytest.raises(helper.ProvisioningError, match='mode'):
        provision(parent)
    assert list(parent[0].iterdir()) == []


def test_full_ancestor_walk_rejects_higher_symlink_and_writable_ancestor(parent, monkeypatch):
    anchor = parent[0]
    (anchor / 'real/inner').mkdir(parents=True)
    (anchor / 'link').symlink_to(anchor / 'real', target_is_directory=True)
    real_open = os.open
    def test_open(path, flags, *args, **kwargs):
        # Root the lexical walker in the isolated tree; all later opens are real.
        return real_open(anchor if path == '/' else path, flags, *args, **kwargs)
    monkeypatch.setattr(os, 'open', test_open)
    with pytest.raises(OSError):
        helper._open_parent(Path('/link/inner'), os.getuid(), os.getgid())
    (anchor / 'real').chmod(0o777)
    with pytest.raises(helper.ProvisioningError, match='mode'):
        helper._open_parent(Path('/real/inner'), os.getuid(), os.getgid())
    assert not (anchor / 'real/inner' / helper.ROOT_NAME).exists()


def test_concurrent_symlink_at_creation_does_not_touch_target(parent, monkeypatch):
    target = parent[0] / 'target'
    target.mkdir(mode=0o700)
    real_mkdir = os.mkdir
    def replace(name, mode=0o777, *, dir_fd=None):
        if name == helper.ROOT_NAME:
            os.symlink(str(target), name, dir_fd=dir_fd)
            raise FileExistsError(name)
        return real_mkdir(name, mode, dir_fd=dir_fd)
    monkeypatch.setattr(os, 'mkdir', replace)
    with pytest.raises(helper.ProvisioningError):
        provision(parent)
    assert list(target.iterdir()) == []


def test_cli_has_no_path_override_and_requires_root(monkeypatch):
    called = []
    monkeypatch.setattr(helper, 'provision_private_roots', lambda: called.append(True))
    monkeypatch.setattr(os, 'geteuid', lambda: 0)
    assert helper.main(['--root', '/tmp/unsafe']) == 2
    assert not called
    monkeypatch.setattr(os, 'geteuid', lambda: 501)
    assert helper.main([]) == 2
    assert not called


@pytest.mark.parametrize('filename', ['update.sh', 'api-setup.sh'])
@pytest.mark.parametrize('helper_status', [0, 9])
def test_actual_deploy_fragment_stops_before_verify_install_restart(tmp_path, filename, helper_status):
    source = (REPO / 'app/deploy' / filename).read_text()
    fragment = source.split('# BEGIN COMPANY_INTELLIGENCE_PRIVATE_ROOTS\n', 1)[1].split('# END COMPANY_INTELLIGENCE_PRIVATE_ROOTS', 1)[0]
    first_verify = source.index('if ! mm_reviewed_unit_file_ready' if filename == 'update.sh' else 'REVIEWED_UNIT_NAMES=(')
    assert source.index('# BEGIN COMPANY_INTELLIGENCE_PRIVATE_ROOTS') < first_verify
    assert source.count('company-intelligence-private-roots.py') == 1
    # Only the interpreter location changes; execute the actual guarded shell call.
    fragment = fragment.replace('/opt/macro-api/.venv/bin/python', '"$TEST_PYTHON"')
    venv = tmp_path / 'venv/bin'
    venv.mkdir(parents=True)
    fake = venv / 'python'
    fake.write_text(f'#!/bin/sh\nprintf "provision\\n" >> "$CALLS"\nexit {helper_status}\n')
    fake.chmod(0o700)
    calls = tmp_path / 'calls'
    env = dict(os.environ, APP_DIR=str(REPO), VENV=str(venv.parent), TEST_PYTHON=str(fake), CALLS=str(calls))
    result = subprocess.run(['bash', '-c', fragment + '\nprintf "verify\\ninstall\\nrestart\\n" >> "$CALLS"\n'], env=env, text=True, capture_output=True)
    assert result.returncode == (0 if helper_status == 0 else 1)
    assert calls.read_text().splitlines() == (['provision', 'verify', 'install', 'restart'] if helper_status == 0 else ['provision'])
    subprocess.run(['bash', '-n', str(REPO / 'app/deploy' / filename)], check=True)


def test_unit_has_nonoptional_corrected_read_and_deny_mounts():
    source = (REPO / 'app/deploy/macro-api.service').read_text()
    paths = [line for line in source.splitlines() if 'Paths=' in line and 'macro-company-intelligence' in line]
    assert paths == [
        'ReadOnlyPaths=/var/lib/macro-company-intelligence/state',
        'ReadOnlyPaths=/var/lib/macro-company-intelligence/artifacts',
        'InaccessiblePaths=/var/lib/macro-company-intelligence/publisher',
    ]
