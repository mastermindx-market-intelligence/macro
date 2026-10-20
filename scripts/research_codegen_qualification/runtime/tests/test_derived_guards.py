"""Additional production-function guards, no process/socket/host execution."""
import json
import os
import pytest
import qualification_smoke as qsm
import test_qualification_smoke as f
from test_qualification_smoke import no_subprocess, sources, comp


def test_client_config_cannot_enable_helpers(tmp_path):
    directory = tmp_path / 'client'
    directory.mkdir(mode=0o700)
    file = directory / 'config.json'
    file.write_bytes(qsm.ANONYMOUS_CLIENT_CONFIG)
    file.chmod(0o600)
    qsm.verify_client_config(str(directory), qsm.ANONYMOUS_CLIENT_CONFIG_SHA256)
    file.write_text('{"auths":{},"credsStore":"pass"}')
    with pytest.raises(qsm.BindingMismatch):
        qsm.verify_client_config(str(directory), qsm.ANONYMOUS_CLIENT_CONFIG_SHA256)


def test_attached_workload_denial_text_never_freezes(comp, monkeypatch):
    captured = comp.t.ProcessResult((), 0, b'Error response from daemon: permission denied\n', False, False, '')
    monkeypatch.setattr(comp.t, 'collect_process', lambda *a, **kw: captured)
    result = qsm._real_executor(comp.t)((qsm.DOCKER_BINARY, '--host', qsm.DOCKER_ENDPOINT,
        '--config', '/owned/client', 'start', '--attach', f.CID), deadline_seconds=1, output_cap_bytes=1024)
    assert not result.permission_refused


def test_receipt_short_writes_complete_before_return(tmp_path, monkeypatch):
    path = tmp_path / 'receipt.jsonl'
    original = os.write
    monkeypatch.setattr(qsm.os, 'write', lambda fd, data: original(fd, data[:7]))
    qsm._write_receipt(str(path), {'phase': 'known_cid', 'container_id': f.CID}, True)
    assert json.loads(path.read_text())['container_id'] == f.CID


def test_receipt_append_cannot_recreate_lost_identity(tmp_path):
    path = tmp_path / 'absent.jsonl'
    with pytest.raises(FileNotFoundError):
        qsm._write_receipt(str(path), {'container_id': f.CID}, False)
    assert not path.exists()


def test_self_cleanup_local_permissionerror_stops_immediately(comp):
    collector = f.FakeCollector(comp, f.policy_doc_ok(comp))
    collector.script['stop'] = PermissionError('synthetic control boundary')
    engine = f.make_engine(comp, collector)
    engine._cid = f.CID
    engine._self_cleanup(f.CID)
    assert engine.frozen
    assert [r['kind'] for r in collector.calls] == ['stop']


def test_every_effective_call_uses_same_owned_config(comp):
    collector = f.FakeCollector(comp, f.policy_doc_ok(comp), state_doc=f.state_doc_ok(f.CID),
                                verdict_out=f.verdict_bytes())
    engine = f.make_engine(comp, collector)
    attempt = f.run_attempt(comp, engine)
    assert attempt.cleanup_confirmed
    for row in collector.calls:
        assert row['argv'][:5] == [qsm.DOCKER_BINARY, '--host', qsm.DOCKER_ENDPOINT,
                                   '--config', f.BINDING_OK['client_config_dir']]


def test_receipt_replacement_inode_cannot_receive_cid(tmp_path):
    path = tmp_path / 'receipt.jsonl'
    identity = qsm._write_receipt(str(path), {'phase': 'pre_create'}, True)
    replacement = tmp_path / 'replacement'
    replacement.write_text('other writer\n')
    replacement.chmod(0o600)
    replacement.replace(path)
    with pytest.raises(OSError):
        qsm._write_receipt(str(path), {'container_id': f.CID}, False,
                           expected_identity=identity)
    assert path.read_text() == 'other writer\n'
