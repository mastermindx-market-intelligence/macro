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


def test_failed_native_download_retains_only_fixed_reported_errors_and_actual_code(tmp_path, monkeypatch):
    item = archive()
    STAGE.retain_once(tmp_path / 'archives.json', [item.__dict__])
    monkeypatch.setattr(STAGE.time, 'monotonic', lambda:0)
    monkeypatch.setattr(STAGE.pwd, 'getpwnam', lambda _:SimpleNamespace(pw_uid=501,pw_gid=20))
    monkeypatch.setattr(STAGE.os, 'chown', lambda *a:None)
    calls = []
    def native(argv, **kwargs):
        calls.append((argv,kwargs))
        return 100, b'E: Failed to fetch https://SECRET:credential@private.invalid/archive.deb Permission denied\n'
    monkeypatch.setattr(STAGE, 'observe_command', native)
    result = STAGE.run_stage(tmp_path, 'download', 0, 600)
    assert result == {'outcome':'failed','settlement':'settled','returncode':100,'reported_errors':['PERMISSION','FETCH']}
    assert len(calls)==1 and calls[0][1]['deadline']==600
    assert b'SECRET' not in STAGE.canonical(result) and b'private.invalid' not in STAGE.canonical(result)
    assert (tmp_path/'download-0').is_dir()  # no cleanup, install or retry


@pytest.mark.parametrize('output,expected', [
    (b'E: Unable to locate package SECRET', ['SELECTION']),
    (b'E: Some packages could not be authenticated SECRET', ['AUTH']),
    (b"E: Couldn't determine mirror list to query for SECRET", ['MIRROR_LIST']),
    (b'E: Failed to fetch SECRET Hash Sum mismatch', ['HASH','FETCH']),
    (b'E: The method driver SECRET could not be found', ['METHOD']),
    (b'opaque SECRET failure', ['UNCLASSIFIED']),
    (b'\xff Permission denied SECRET', ['UNCLASSIFIED']),
    (b'\x00 Permission denied SECRET', ['UNCLASSIFIED']),
    ('Permission denied SECRET', ['UNCLASSIFIED']),
    (b'x' * (STAGE.LIMIT+1), ['UNCLASSIFIED']),
])
def test_native_reported_error_categories_are_finite_bounded_and_never_echo_private_output(output,expected):
    result = STAGE.reported_download_errors(output)
    assert result == expected
    assert set(result) <= set(STAGE.REPORTED_ERROR_CODES)
    assert 'SECRET' not in json.dumps(result)


@pytest.mark.parametrize('value', [None,[], 'AUTH', {'AUTH':'SECRET'}, ['SECRET'], ['AUTH','AUTH'],
                                  ['AUTH',{'raw':'SECRET'}], ['UNCLASSIFIED','AUTH'], ['AUTH']*100])
def test_native_diagnostic_boundary_rejects_malformed_or_untrusted_enum_payload(value):
    assert STAGE.sanitize_reported_errors(value) == ['UNCLASSIFIED']


def completion_prepared(tmp_path,monkeypatch):
    from dataclasses import replace
    import hashlib
    first=archive();second=replace(first,package='second-font',filename='second-font_1.0_all.deb',sha256=hashlib.sha256(b'next').hexdigest(),uri='http://azure.archive.ubuntu.com/ubuntu/pool/main/s/second-font/second-font_1.0_all.deb')
    records=[first,second];tx=transaction();tx['packages'].append({**copy.deepcopy(tx['packages'][0]),'name':'second-font'})
    STAGE.retain_once(tmp_path/'archives.json',[a.__dict__ for a in records]);STAGE.retain_once(tmp_path/'frozen-native.json',tx)
    for i,outcome in enumerate(['passed','failed']):
        d=tmp_path/f'download-{i}';d.mkdir()
        if i==0:(d/first.filename).write_bytes(b'data')
        row={'mode':'download','index':i,'outcome':outcome,'settlement':'settled','returncode':0 if i==0 else 100}
        if i==1:row['reported_errors']=['FETCH']
        STAGE.retain_once(tmp_path/f'download-result-{i}.json',row)
    monkeypatch.setattr(STAGE.time,'monotonic',lambda:100)
    monkeypatch.setattr(STAGE.pwd,'getpwnam',lambda _:SimpleNamespace(pw_uid=os.geteuid(),pw_gid=os.getegid()))
    monkeypatch.setattr(STAGE.os,'chown',lambda *a:None)
    verify=STAGE.verify_file
    monkeypatch.setattr(STAGE,'verify_file',lambda path,expected,**kwargs:verify(path,expected,immutable=False))
    monkeypatch.setattr(STAGE,'completion_download_argv',lambda **kw:('native-completion',kw['cache']))
    return records,tx


def test_native_completion_reuses_only_verified_archives_and_proves_entire_frozen_transaction(tmp_path,monkeypatch):
    records,tx=completion_prepared(tmp_path,monkeypatch);events=[]
    def native(argv,**kw):
        events.append((argv,kw));assert kw['deadline']==600
        if argv==STAGE.trusted_package_indexes_argv():return 0,b'yes\n'
        cache=tmp_path/'completion-cache'
        assert (cache/records[0].filename).read_bytes()==b'data' and not (cache/records[1].filename).exists()
        (cache/records[1].filename).write_bytes(b'next');STAGE.retain_once(tmp_path/'completion-native.json',tx)
        return 0,b'complete'
    monkeypatch.setattr(STAGE,'observe_command',native)
    with STAGE.acquisition_admission(tmp_path,'complete'):
        result=STAGE.run_stage(tmp_path,'complete',None,600)
    assert result=={'outcome':'passed','settlement':'settled','returncode':0}
    assert len(events)==2 and STAGE.read_json(tmp_path/'completion-verified.json')==[a.__dict__ for a in records]
    assert (tmp_path/'download-0'/records[0].filename).read_bytes()==b'data'
    assert not (tmp_path/'download-1'/records[1].filename).exists()  # no failed selector replay/rewrite
    assert STAGE.read_json(tmp_path/'download-result-1.json')['outcome']=='failed'
    with pytest.raises(STAGE.AcquisitionRefused,match='COMPLETION_ALREADY_ATTEMPTED'):
        with STAGE.acquisition_admission(tmp_path,'complete'):pytest.fail('no repeat completion')
    with pytest.raises(STAGE.AcquisitionRefused,match='COMPLETION_ALREADY_ATTEMPTED'):
        with STAGE.acquisition_admission(tmp_path,'download'):pytest.fail('no later selector launch')


@pytest.mark.parametrize('fault',['trust-no','trust-empty','trust-exit','missing','hash','transaction','response-loss','nonzero','sandbox','symlink'])
def test_native_completion_faults_preserve_originals_and_refuse_install_cleanup_or_new_attempt(tmp_path,monkeypatch,fault):
    records,tx=completion_prepared(tmp_path,monkeypatch);events=[]
    def native(argv,**kw):
        events.append(argv)
        if argv==STAGE.trusted_package_indexes_argv():
            return (100,b'') if fault=='trust-exit' else (0,b'no\n' if fault=='trust-no' else b'' if fault=='trust-empty' else b'yes\n')
        if fault=='response-loss':raise STAGE.NativeUnknown('original uncertain',4242)
        cache=tmp_path/'completion-cache'
        if fault=='symlink':(cache/records[1].filename).symlink_to(cache/records[0].filename)
        elif fault!='missing':(cache/records[1].filename).write_bytes(b'evil' if fault=='hash' else b'next')
        actual=copy.deepcopy(tx)
        if fault=='transaction':actual['packages'][0]['automatic']=True
        STAGE.retain_once(tmp_path/'completion-native.json',actual)
        return (100,b'') if fault=='nonzero' else (0,b'unsandboxed' if fault=='sandbox' else b'complete')
    monkeypatch.setattr(STAGE,'observe_command',native)
    with pytest.raises(Exception):
        with STAGE.acquisition_admission(tmp_path,'complete'):STAGE.run_stage(tmp_path,'complete',None,600)
    assert (tmp_path/'completion-attempt').is_dir() and not (tmp_path/'completion-verified.json').exists()
    assert STAGE.read_json(tmp_path/'download-result-1.json')['outcome']=='failed'
    assert not (tmp_path/'install-attempt').exists()
    assert len(events)==(1 if fault.startswith('trust-') else 2)


@pytest.mark.parametrize('fault',['unknown','AUTH','HASH','PERMISSION','METHOD','MIRROR_LIST','UNCLASSIFIED','missing-receipt','partial','deadline'])
def test_native_completion_admission_cannot_promote_unverified_inputs(tmp_path,monkeypatch,fault):
    records,tx=completion_prepared(tmp_path,monkeypatch)
    if fault=='deadline':monkeypatch.setattr(STAGE.time,'monotonic',lambda:600)
    elif fault=='partial':(tmp_path/'download-0'/records[0].filename).write_bytes(b'bad')
    else:
        p=tmp_path/'download-result-1.json';row=STAGE.read_json(p);p.unlink()
        if fault!='missing-receipt':
            if fault=='unknown':row['settlement']='unknown'
            else:row['reported_errors']=[fault]
            STAGE.retain_once(p,row)
    monkeypatch.setattr(STAGE,'observe_command',lambda *a,**k:pytest.fail('no native completion on unqualified input'))
    with pytest.raises(Exception):
        with STAGE.acquisition_admission(tmp_path,'complete'):STAGE.run_stage(tmp_path,'complete',None,600)
    assert not (tmp_path/'completion-attempt').exists()


def test_native_completion_admission_lock_refuses_existing_reader_and_symlink(tmp_path):
    with STAGE.acquisition_admission(tmp_path,'download'):
        with pytest.raises(BlockingIOError):
            with STAGE.acquisition_admission(tmp_path,'complete'):pytest.fail('active native child')
    (tmp_path/'acquisition.lock').unlink();(tmp_path/'acquisition.lock').symlink_to(tmp_path/'foreign')
    with pytest.raises(OSError):
        with STAGE.acquisition_admission(tmp_path,'complete'):pytest.fail('symlink lock')


def test_native_completion_marker_sync_failure_precedes_any_native_effect(tmp_path,monkeypatch):
    completion_prepared(tmp_path,monkeypatch)
    monkeypatch.setattr(STAGE,'sync_directory',lambda *a:(_ for _ in ()).throw(OSError('sync unavailable')))
    monkeypatch.setattr(STAGE,'observe_command',lambda *a,**k:pytest.fail('marker must be persisted before effect'))
    with pytest.raises(OSError):
        with STAGE.acquisition_admission(tmp_path,'complete'):STAGE.run_stage(tmp_path,'complete',None,600)
    assert (tmp_path/'completion-attempt').is_dir()


def test_original_native_download_result_survives_response_loss(tmp_path,monkeypatch):
    monkeypatch.setattr(STAGE,'root_directory',lambda:tmp_path)
    monkeypatch.setattr(STAGE.sys,'argv',['stage','download','600','0'])
    result={'outcome':'failed','settlement':'settled','returncode':100,'reported_errors':['FETCH']}
    monkeypatch.setattr(STAGE,'run_stage',lambda *a:copy.deepcopy(result))
    class LostResponse:
        def write(self,*a):raise OSError('response lost after result retention')
    monkeypatch.setattr(STAGE.sys,'stdout',SimpleNamespace(buffer=LostResponse()))
    with pytest.raises(OSError):STAGE.main()
    retained=STAGE.read_json(tmp_path/'download-result-0.json')
    assert retained=={**result,'mode':'download','index':0}


@pytest.mark.parametrize('changed',[False,True])
def test_completion_json_hook_preserves_frozen_transaction_and_requires_exact_actions(tmp_path,changed):
    STAGE.json_hook(tmp_path,Duplex(hook_messages(transaction())))
    original=(tmp_path/'frozen-native.json').read_bytes();(tmp_path/'completion-attempt').mkdir()
    tx=transaction()
    if changed:tx['packages'][0]['automatic']=True
    if changed:
        with pytest.raises(ValueError):STAGE.json_hook(tmp_path,Duplex(hook_messages(tx)))
        assert not (tmp_path/'completion-native.json').exists()
    else:
        STAGE.json_hook(tmp_path,Duplex(hook_messages(tx)))
        assert STAGE.read_json(tmp_path/'completion-native.json')==STAGE.read_json(tmp_path/'frozen-native.json')
    assert (tmp_path/'frozen-native.json').read_bytes()==original and not (tmp_path/'actual-native.json').exists()


@pytest.mark.parametrize('tampered',[False,True])
def test_existing_no_download_install_requires_exact_completed_members(tmp_path,monkeypatch,tampered):
    records,tx=completion_prepared(tmp_path,monkeypatch)
    (tmp_path/'completion-attempt').mkdir();cache=tmp_path/'completion-verified-cache';cache.mkdir()
    for archive,data in zip(records,[b'data',b'next']):(cache/archive.filename).write_bytes(data)
    witness=[a.__dict__ for a in records]
    if tampered:witness[0]={**witness[0],'sha256':'0'*64}
    STAGE.retain_once(tmp_path/'completion-verified.json',witness)
    monkeypatch.setattr(STAGE,'no_download_install_argv',lambda **kw:('existing-no-download-install',kw['cache']))
    calls=[]
    def native(argv,**kw):
        calls.append(argv);assert kw['deadline']==600
        for archive,data in zip(records,[b'data',b'next']):assert (tmp_path/'install-cache'/archive.filename).read_bytes()==data
        STAGE.retain_once(tmp_path/'actual-native.json',tx);STAGE.retain_once(tmp_path/'preinstall-actions.json',[])
        return 0,b''
    monkeypatch.setattr(STAGE,'observe_command',native)
    monkeypatch.setattr(STAGE,'validate_actions',lambda frozen,actions,inventory,path,**kw:None)
    if tampered:
        with pytest.raises(STAGE.AcquisitionRefused,match='COMPLETION_ARCHIVES_UNPROVEN'):
            with STAGE.acquisition_admission(tmp_path,'install'):STAGE.run_stage(tmp_path,'install',None,600)
        assert not calls
    else:
        with STAGE.acquisition_admission(tmp_path,'install'):
            assert STAGE.run_stage(tmp_path,'install',None,600)['outcome']=='passed' and len(calls)==1
    assert STAGE.read_json(tmp_path/'download-result-1.json')['outcome']=='failed'


def test_native_completion_privileged_stage_refuses_existing_install_attempt(tmp_path,monkeypatch):
    completion_prepared(tmp_path,monkeypatch)
    (tmp_path/'install-attempt').mkdir()
    monkeypatch.setattr(STAGE,'observe_command',lambda *a,**k:pytest.fail('prior install cannot authorize new acquisition'))
    with pytest.raises(STAGE.AcquisitionRefused,match='INSTALL_ALREADY_ATTEMPTED'):
        with STAGE.acquisition_admission(tmp_path,'complete'):STAGE.run_stage(tmp_path,'complete',None,600)
    assert (tmp_path/'install-attempt').is_dir() and not (tmp_path/'completion-attempt').exists()
    assert STAGE.read_json(tmp_path/'download-result-1.json')['outcome']=='failed'


@pytest.mark.parametrize('first,second',[('complete','install'),('install','complete')])
def test_completion_install_forced_interleaving_excludes_other_phase_before_marker(tmp_path,first,second):
    import threading
    entered=threading.Event();release=threading.Event();holder_errors=[];second_effects=[]
    def holder():
        try:
            with STAGE.acquisition_admission(tmp_path,first):
                # Pause after admission/check and BEFORE the phase marker.
                entered.set()
                if not release.wait(5):raise AssertionError('test release missing')
                (tmp_path/('completion-attempt' if first=='complete' else 'install-attempt')).mkdir()
        except BaseException as error:holder_errors.append(error)
    thread=threading.Thread(target=holder);thread.start()
    try:
        assert entered.wait(5) and not holder_errors
        assert not (tmp_path/'completion-attempt').exists() and not (tmp_path/'install-attempt').exists()
        with pytest.raises(BlockingIOError):
            with STAGE.acquisition_admission(tmp_path,second):
                second_effects.append(second)
                (tmp_path/('completion-attempt' if second=='complete' else 'install-attempt')).mkdir()
    finally:
        release.set();thread.join(5)
    assert not thread.is_alive() and not holder_errors and not second_effects
    assert (tmp_path/('completion-attempt' if first=='complete' else 'install-attempt')).is_dir()
    assert not (tmp_path/('completion-attempt' if second=='complete' else 'install-attempt')).exists()
