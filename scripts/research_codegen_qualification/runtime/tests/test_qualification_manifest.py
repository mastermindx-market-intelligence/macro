"""Invented installer-result documents only; no runtime or host claims."""
import copy
import hashlib
import json
import sys
from pathlib import Path
import pytest
import qualification_manifest as m
import qualification_runsc_smoke as smoke


def successful_result():
    pins = {name: hashlib.sha256(name.encode()).hexdigest() for name in m.SIZES}
    pins['runsc'] = m.RUNSC
    return {'schema': 'mastermind.rf_runsc_install_receipt.v2', 'root_id': m.ROOT,
            'operation_id': 'fixture-op', 'status': 'OK_INSTALLED', 'exit_code': 0,
            'receipt_write_failed': False, 'unknowns': [], 'rollback': {},
            'host': {'hostname': 'fixture-host', 'uid': 0, 'platform': ['Linux', 'x86_64']},
            'docker_endpoint': m.ENDPOINT,
            'docker': {'daemon_id': 'fixture-daemon', 'client_version': '29.1.3', 'server_version': '29.1.3',
                       'container_total': 0, 'container_running': 0, 'default_runtime': 'runc'},
            'settlement': {'confirmed': True, 'verified': True, 'outcome': 'VERIFIED',
                           'default_runtime': 'runc', 'runtime_names': ['runc', 'rf-runsc']},
            'archive': {'sha256': m.ARCHIVE, 'size_bytes': 166822039},
            'bundle': {'version_dir': m.CONSUMER.rsplit('/', 1)[0],
                       'runtime_entry': {'path': m.CONSUMER, 'runtimeArgs': m.ARGS},
                       'member_sha256': pins, 'member_sizes': dict(m.SIZES),
                       'created': True, 'reused': False, 'shim_installed': False},
            'binding': {'root_id': m.ROOT, 'operation_id': 'fixture-op', 'member_sha256': pins},
            'config': {'path': '/etc/docker/daemon.json', 'commit_uncertain': False, 'committed': True,
                       'additive_diff_asserted': True, 'postimage_sha256': 'a' * 64,
                       'preimage_sha256': 'b' * 64},
            'commands': [{'rc': 0, 'timed_out': False, 'truncated': False, 'refused': False}]}


def project(doc):
    raw = json.dumps(doc).encode()
    return m.project_installer_result(raw, expected_sha256=hashlib.sha256(raw).hexdigest(),
                                     expected_operation='fixture-op', expected_hostname='fixture-host',
                                     expected_daemon_id='fixture-daemon')


def test_success_projects_exact_actual_smoke_schema_without_input_mutation():
    doc = successful_result(); before = copy.deepcopy(doc)
    result = project(doc)
    assert smoke._manifest_problem(result, {'expected_hostname': 'fixture-host'}) is None
    assert result['config_sha256'] == 'a' * 64
    assert doc == before


def test_reuse_projects_verified_preimage_not_missing_postimage():
    doc = successful_result(); doc['status'] = 'OK_REUSE_EXISTING'
    doc['bundle'].update(created=False, reused=True)
    doc['config'].update(committed=False, additive_diff_asserted=False, postimage_sha256=None)
    assert project(doc)['config_sha256'] == 'b' * 64


@pytest.mark.parametrize('path,value', [
    (('status',), 'UNKNOWN_RELOAD_SETTLEMENT'), (('status',), 'OK_ROLLED_BACK'),
    (('exit_code',), False), (('receipt_write_failed',), True),
    (('root_id',), 'other'), (('operation_id',), 'other'),
    (('host', 'hostname'), 'other'), (('host', 'uid'), False),
    (('docker', 'daemon_id'), 'other'), (('docker', 'container_total'), 1),
    (('settlement', 'verified'), False), (('config', 'commit_uncertain'), True),
    (('config', 'committed'), False), (('config', 'postimage_sha256'), None),
    (('bundle', 'shim_installed'), True), (('bundle', 'member_sha256', 'runsc'), '0' * 64),
    (('commands', 0, 'truncated'), True), (('commands', 0, 'timed_out'), True),
    (('commands', 0, 'refused'), True), (('unknowns',), ['partial']),
])
def test_unsettled_or_wrong_identity_refuses(path, value):
    doc = successful_result(); item = doc
    for key in path[:-1]: item = item[key]
    item[path[-1]] = value
    with pytest.raises(m.ProjectionRefused): project(doc)


def test_raw_malformed_or_wrong_digest_refuses():
    for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'[]', b'x' * 262145):
        with pytest.raises(m.ProjectionRefused):
            m.project_installer_result(raw, expected_sha256=hashlib.sha256(raw).hexdigest(),
                                      expected_operation='fixture-op', expected_hostname='fixture-host',
                                      expected_daemon_id='fixture-daemon')
    raw = json.dumps(successful_result()).encode()
    with pytest.raises(m.ProjectionRefused, match='raw result digest'):
        m.project_installer_result(raw, expected_sha256='c' * 64, expected_operation='fixture-op',
                                  expected_hostname='fixture-host', expected_daemon_id='fixture-daemon')
