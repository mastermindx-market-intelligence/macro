"""Synthetic native-hook/file/process boundaries; never run APT, sudo or root helpers."""
import copy
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import ci_apt_native_stage as STAGE
from scripts.ci_apt_cold_acquisition import AcquisitionRefused, Archive
from scripts.ci_apt_native_plan import DIRECT_PACKAGES


def archive():
    import hashlib
    return Archive('font-fixture', '1.0', 'amd64', 'all', 'font-fixture_1.0_all.deb', 4,
                   hashlib.sha256(b'data').hexdigest(), 'http://azure.archive.ubuntu.com/ubuntu/pool/main/f/font-fixture/font-fixture_1.0_all.deb')


def transaction():
    return {'command': 'install', 'search-terms': list(DIRECT_PACKAGES), 'packages': [
        {'name': 'font-fixture', 'architecture': 'amd64', 'mode': 'install', 'automatic': False,
         'versions': {'install': {'version': '1.0', 'architecture': 'all', 'pin': 500, 'origins': []}}}]}


def prepared(tmp_path, monkeypatch):
    item = archive(); cache = tmp_path / 'install-cache'; cache.mkdir()
    (cache / item.filename).write_bytes(b'data')
    for name in ('frozen-native.json', 'actual-native.json'):
        STAGE.retain_once(tmp_path / name, transaction())
    STAGE.retain_once(tmp_path / 'archives.json', [item.__dict__])
    monkeypatch.setenv('APT_HOOK_INFO_FD', '0'); monkeypatch.setenv('DPKG_FRONTEND_LOCKED', 'true')
    # Synthetic user-owned temp files. Exercise byte checks, but do not claim
    # these fixtures prove actual privileged staging ownership.
    verify = STAGE.verify_file
    def synthetic_verify(path, expected, *, immutable):
        assert immutable is True
        verify(path, expected, immutable=False)
    monkeypatch.setattr(STAGE, 'verify_file', synthetic_verify)
    return item


def frame(tmp_path, **changes):
    config = {'APT::Get::Download': 'false', 'APT::Get::Fix-Missing': 'false',
              'APT::Get::AllowUnauthenticated': 'false', 'Debug::NoLocking': 'false',
              'Acquire::AllowInsecureRepositories': 'false', 'Acquire::AllowDowngradeToInsecureRepositories': 'false'}
    config.update(changes)
    lines = [f'{key}={value}' for key, value in config.items() if value is not None]
    # Secret-like inherited configuration is consumed privately, never in the
    # returned action record or a fixed refusal message.
    lines.append('Acquire::http::Proxy=http://SECRET:credential@proxy.invalid')
    return ('VERSION 3\n' + '\n'.join(lines) + '\n\n' +
            f'font-fixture - - none < 1.0 all foreign {tmp_path}/install-cache/font-fixture_1.0_all.deb\n' +
            'font-fixture - - none < 1.0 all foreign **CONFIGURE**\n').encode()


def test_locked_hook_rechecks_full_transaction_and_exact_archive_before_dpkg(tmp_path, monkeypatch):
    prepared(tmp_path, monkeypatch)
    STAGE.preinstall_hook(tmp_path, frame(tmp_path))
    result = STAGE.read_json(tmp_path / 'preinstall-actions.json')
    assert len(result) == 2 and result[0]['newarch'] == 'all'
    assert b'SECRET' not in (tmp_path / 'preinstall-actions.json').read_bytes()


@pytest.mark.parametrize('fault', ['version', 'architecture', 'auto', 'origin', 'missing-action', 'extra-action',
                                   'missing-archive', 'partial', 'hash', 'symlink', 'foreign-path', 'old-protocol',
                                   'missing-control', 'fix-missing', 'download', 'missing-lock', 'duplicate-control'])
def test_locked_final_fence_refuses_drift_missing_or_raced_members_before_action_receipt(tmp_path, monkeypatch, fault):
    item = prepared(tmp_path, monkeypatch)
    raw = frame(tmp_path)
    actual = transaction()
    if fault in {'version', 'architecture', 'auto', 'origin'}:
        if fault == 'version': actual['packages'][0]['versions']['install']['version'] = '2.0'
        if fault == 'architecture': actual['packages'][0]['architecture'] = 'arm64'
        if fault == 'auto': actual['packages'][0]['automatic'] = True
        if fault == 'origin': actual['packages'][0]['versions']['install']['origins'] = [{'site': 'foreign'}]
        (tmp_path / 'actual-native.json').write_text(json.dumps(actual))
    if fault == 'missing-action': raw = raw.split(b'\n\n')[0] + b'\n\n'
    if fault == 'extra-action': raw += b'extra-package - - none < 1.0 all foreign **CONFIGURE**\n'
    if fault == 'missing-archive': (tmp_path / 'install-cache' / item.filename).unlink()
    if fault == 'partial': (tmp_path / 'install-cache' / item.filename).write_bytes(b'dat')
    if fault == 'hash': (tmp_path / 'install-cache' / item.filename).write_bytes(b'evil')
    if fault == 'symlink':
        path = tmp_path / 'install-cache' / item.filename; path.unlink(); path.symlink_to(tmp_path / 'frozen-native.json')
    if fault == 'foreign-path': raw = raw.replace(str(tmp_path / 'install-cache').encode(), b'/foreign')
    if fault == 'old-protocol': raw = raw.replace(b'VERSION 3', b'VERSION 2')
    if fault == 'missing-control': raw = frame(tmp_path, **{'APT::Get::Download': None})
    if fault == 'fix-missing': raw = frame(tmp_path, **{'APT::Get::Fix-Missing': 'true'})
    if fault == 'download': raw = frame(tmp_path, **{'APT::Get::Download': 'true'})
    if fault == 'missing-lock': monkeypatch.delenv('DPKG_FRONTEND_LOCKED')
    if fault == 'duplicate-control': raw = raw.replace(b'\n\n', b'\nAPT::Get::Download=false\n\n')
    with pytest.raises((ValueError, OSError)) as caught:
        STAGE.preinstall_hook(tmp_path, raw)
    assert 'SECRET' not in str(caught.value)
    assert not (tmp_path / 'preinstall-actions.json').exists()


def test_adoption_checks_one_open_descriptor_and_refuses_replaced_source(tmp_path, monkeypatch):
    source = tmp_path / 'source'; source.write_bytes(b'data'); target = tmp_path / 'target'
    original = STAGE.os.fstat; calls = 0
    def raced(fd):
        nonlocal calls
        calls += 1
        info = original(fd)
        if calls == 2:
            source.unlink(); source.write_bytes(b'data')
        return info
    monkeypatch.setattr(STAGE.os, 'fstat', raced)
    with pytest.raises(AcquisitionRefused, match='ARCHIVE_BYTES_CHANGED'):
        STAGE.adopt_archive(source, target, archive())
    assert target.stat().st_mode & 0o777 == 0o600


def test_adoption_is_nonoverwriting_and_only_publishes_verified_bytes(tmp_path):
    source = tmp_path / 'source'; source.write_bytes(b'data'); target = tmp_path / 'target'
    STAGE.adopt_archive(source, target, archive())
    assert target.read_bytes() == b'data' and target.stat().st_mode & 0o777 == 0o644
    with pytest.raises(FileExistsError): STAGE.adopt_archive(source, target, archive())
    assert target.read_bytes() == b'data'


def test_private_retention_refuses_symlink_conflict_and_does_not_overwrite(tmp_path):
    path = tmp_path / 'result'; STAGE.retain_once(path, {'a': 1})
    STAGE.retain_once(path, {'a': 1})
    with pytest.raises(AcquisitionRefused): STAGE.retain_once(path, {'a': 2})
    other = tmp_path / 'link'; other.symlink_to(path)
    with pytest.raises(OSError): STAGE.read_json(other)
    assert STAGE.read_json(path) == {'a': 1}


class Duplex:
    def __init__(self, raw): self.input = io.BytesIO(raw); self.output = io.BytesIO()
    def readline(self, n): return self.input.readline(n)
    def write(self, data): return self.output.write(data)
    def flush(self): pass


def hook_messages(tx):
    # Genuine native schema, not a hydration helper for malformed fixtures.
    row = copy.deepcopy(tx['packages'][0]); row['id'] = 1
    for version in row['versions'].values(): version['id'] = 2
    hello = {'jsonrpc':'2.0','method':'org.debian.apt.hooks.hello','id':0,'params':{'versions':['0.1','0.2']}}
    event = {'jsonrpc':'2.0','method':'org.debian.apt.hooks.install.pre-prompt','params':{**tx,'unknown-packages':[],'packages':[row]}}
    bye = {'jsonrpc':'2.0','method':'org.debian.apt.hooks.bye','params':{}}
    return b''.join(json.dumps(m).encode() + b'\n\n' for m in (hello,event,bye))


def test_native_json_hook_negotiates_and_never_replaces_frozen_transaction(tmp_path):
    first = Duplex(hook_messages(transaction())); STAGE.json_hook(tmp_path, first)
    assert b'"0.2"' in first.output.getvalue()
    original = (tmp_path / 'frozen-native.json').read_bytes()
    (tmp_path / 'install-attempt').mkdir()
    changed = transaction(); changed['packages'][0]['automatic'] = True
    with pytest.raises(ValueError): STAGE.json_hook(tmp_path, Duplex(hook_messages(changed)))
    assert (tmp_path / 'frozen-native.json').read_bytes() == original
    assert not (tmp_path / 'actual-native.json').exists()


@pytest.mark.parametrize('fault', ['read', 'poll', 'wait', 'deadline'])
def test_native_observation_fault_after_launch_is_unknown_with_original_handle(monkeypatch, fault):
    readfd, writefd = os.pipe(); os.write(writefd, b'bounded'); os.close(writefd)
    output = os.fdopen(readfd, 'rb', buffering=0)
    def poll():
        if fault == 'poll': raise OSError('private observation')
        return 0
    def wait(**kwargs):
        if fault == 'wait': raise OSError('private observation')
        return 0
    process = SimpleNamespace(pid=4242, stdout=output, poll=poll, wait=wait)
    monkeypatch.setattr(STAGE.subprocess, 'Popen', lambda *a, **k: process)
    tick = iter([0, 2] if fault == 'deadline' else [0] * 100)
    monkeypatch.setattr(STAGE.time, 'monotonic', lambda: next(tick))
    if fault == 'read': monkeypatch.setattr(STAGE.os, 'read', lambda *a: (_ for _ in ()).throw(OSError('private read')))
    try:
        with pytest.raises(STAGE.NativeUnknown) as caught: STAGE.observe_command(('not-executed',), deadline=1)
        assert caught.value.child_pid == 4242
        assert caught.value.outcome == ('timed_out' if fault == 'deadline' else 'failed')
        assert 'private' not in str(caught.value)
    finally: output.close()


def test_native_positive_exit_and_eof_is_observed_without_replay(monkeypatch):
    readfd, writefd = os.pipe(); os.write(writefd, b'bounded'); os.close(writefd)
    output = os.fdopen(readfd, 'rb', buffering=0); calls=[]
    process = SimpleNamespace(pid=4242, stdout=output, poll=lambda:0, wait=lambda **k:0)
    monkeypatch.setattr(STAGE.subprocess, 'Popen', lambda *a, **k: calls.append(k) or process)
    monkeypatch.setattr(STAGE.time, 'monotonic', lambda:0)
    assert STAGE.observe_command(('not-executed',), deadline=1, command_env={'DPKG_FRONTEND_LOCKED':'true'}) == (0,b'bounded')
    assert len(calls) == 1 and 'DPKG_FRONTEND_LOCKED' not in calls[0]['env']


@pytest.mark.parametrize('fault',['missing-archive','missing-hook-receipt','native-install-failure'])
def test_native_install_cannot_call_download_or_pass_without_final_hook_and_actual_completion(tmp_path,monkeypatch,fault):
    item=prepared(tmp_path,monkeypatch)
    # run_stage creates the install cache itself, so replace the fixture cache
    # with fresh per-archive source output; no actual privileged operation.
    (tmp_path/'install-cache'/item.filename).unlink();(tmp_path/'install-cache').rmdir()
    source=tmp_path/'download-0';source.mkdir()
    if fault!='missing-archive':(source/item.filename).write_bytes(b'data')
    monkeypatch.setattr(STAGE,'apt_directory',lambda p:p.mkdir())
    # Compiler already has its own closed-path tests. This synthetic root is
    # intentionally on evidence SSD, not a real privileged /tmp installation.
    compiler=STAGE.no_download_install_argv
    monkeypatch.setattr(STAGE,'no_download_install_argv',lambda **k:compiler(hook='/tmp/ci-apt-fixture/txn-hook',cache='/tmp/ci-apt-fixture/install-cache'))
    calls=[]
    def native(argv,**kwargs):
        calls.append(argv)
        assert '--no-download' in argv and 'download' not in argv
        return (100 if fault=='native-install-failure' else 0),b''
    monkeypatch.setattr(STAGE,'observe_command',native)
    monkeypatch.setattr(STAGE.time,'monotonic',lambda:0)
    with pytest.raises((ValueError,OSError,STAGE.NativeUnknown)):
        STAGE.run_stage(tmp_path,'install',None,600)
    assert len(calls)==(0 if fault=='missing-archive' else 1)
    assert (tmp_path/'install-attempt').exists()
    assert source.exists()  # no cleanup/replacement on failure


def test_native_successful_postinstall_archive_removal_preserves_actual_hook_proof(tmp_path,monkeypatch):
    item=prepared(tmp_path,monkeypatch)
    (tmp_path/'install-cache'/item.filename).unlink();(tmp_path/'install-cache').rmdir()
    source=tmp_path/'download-0';source.mkdir();(source/item.filename).write_bytes(b'data')
    monkeypatch.setattr(STAGE,'apt_directory',lambda p:p.mkdir())
    compiler=STAGE.no_download_install_argv
    monkeypatch.setattr(STAGE,'no_download_install_argv',lambda **k:compiler(hook='/tmp/ci-apt-fixture/txn-hook',cache='/tmp/ci-apt-fixture/install-cache'))
    def native(argv,**kwargs):
        STAGE.preinstall_hook(tmp_path,frame(tmp_path))
        # Static native private-install.cc453–460: inherited
        # Keep-Downloaded-Packages=false may remove its own completed archives.
        (tmp_path/'install-cache'/item.filename).unlink()
        return 0,b''
    monkeypatch.setattr(STAGE,'observe_command',native)
    monkeypatch.setattr(STAGE.time,'monotonic',lambda:0)
    assert STAGE.run_stage(tmp_path,'install',None,600)['outcome']=='passed'
    assert len(STAGE.read_json(tmp_path/'preinstall-actions.json'))==2
