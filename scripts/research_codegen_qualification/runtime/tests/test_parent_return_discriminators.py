"""Independent parent discriminators; fictional files/executors only."""
import hashlib
import pytest
import qualification_smoke as qsm
import qualification_runsc_smoke as qrs
import test_qualification_smoke as fixtures
from test_qualification_smoke import no_subprocess, sources, comp

@pytest.mark.parametrize('verb', ['inspect', 'info', 'image'])
def test_actual_executor_rc0_trusted_control_denial_freezes(comp, monkeypatch, verb):
    raw = b'{}\nError response from daemon: authorization denied by plugin synthetic\n'
    captured = comp.t.ProcessResult((), 0, raw, False, False, 'synthetic control error')
    monkeypatch.setattr(comp.t, 'collect_process', lambda *a, **kw: captured)
    result = qsm._real_executor(comp.t)((qsm.DOCKER_BINARY, '--host', qsm.DOCKER_ENDPOINT, '--config', '/owned/test-client', verb),
        deadline_seconds=1, output_cap_bytes=1024)
    assert result.permission_refused, 'rc0 trusted control error is not success or ordinary cleanup permission'

def test_actual_collector_permissionerror_freezes(comp, monkeypatch):
    captured = comp.t.ProcessResult((), None, b'', False, False, 'collector failure', 'PermissionError')
    monkeypatch.setattr(comp.t, 'collect_process', lambda *a, **kw: captured)
    result = qsm._real_executor(comp.t)((qsm.DOCKER_BINARY, '--host', qsm.DOCKER_ENDPOINT, '--config', '/owned/test-client', 'inspect'),
        deadline_seconds=1, output_cap_bytes=1024)
    assert result.permission_refused, 'collector typed PermissionError must freeze'

def test_interrupted_sink_cleanup_refusal_prevents_later_mutations(comp):
    collector = fixtures.FakeCollector(comp, fixtures.policy_doc_ok(comp))
    collector.script['stop'] = fixtures.res(comp.t, 126, b'permission denied\n')
    engine = fixtures.make_engine(comp, collector)
    engine._cid = fixtures.CID
    engine._self_cleanup(fixtures.CID)
    assert [r['kind'] for r in collector.calls] == ['stop'], 'finally cleanup must respect frozen state'

def test_bundle_verifier_refuses_missing_five_sidecars(tmp_path, monkeypatch):
    consumer = tmp_path / '20261005.0' / 'runsc'
    consumer.parent.mkdir()
    consumer.write_bytes(b'fake reviewed runsc bytes')
    config = tmp_path / 'daemon.json'
    config.write_bytes(b'{}')
    manifest = fixtures.manifest_ok()
    monkeypatch.setattr(qrs, 'CONSUMER_PATH', str(consumer))
    manifest['consumer_path'] = str(consumer)
    from types import SimpleNamespace
    real_lstat = qrs.os.lstat
    monkeypatch.setattr(qrs.os, 'lstat', lambda p: SimpleNamespace(
        st_mode=0o40755, st_uid=0, st_gid=0) if str(p) == str(consumer.parent) else real_lstat(p))

    with pytest.raises(qsm.SourceContractError):
        qrs.verify_installed_bundle(manifest)

def test_manifest_rejects_arbitrary_private_config_path():
    manifest = fixtures.manifest_ok()
    manifest['config_path'] = '/unapproved/private/file'
    assert qrs._manifest_problem(manifest, fixtures.BINDING_OK) is not None
