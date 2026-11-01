"""Runtime configuration projection, including an opt-in real CLI/fake API check.

The fake API owns a fresh Unix socket; no real daemon, registry, saved client
configuration, credential helper, or service is used. Local client evidence is
version-labelled and cannot qualify the pinned production client by itself.
"""
import copy
import http.server
import json
import os
from pathlib import Path
import re
import socketserver
import subprocess
import tempfile
import threading

import pytest
import test_runsc_install as fixtures

mod = fixtures.mod
TEMPLATE = ('{ {{ $first := true }}{{range $name, $runtime := .Runtimes}}'
            '{{if not $first}},{{end}}{{ $first = false }}'
            '{{json $name}}:{{json $runtime.Runtime}}{{end}} }')


def test_installer_requests_configuration_projection():
    installer = mod.InstallEngine.__new__(mod.InstallEngine)
    observed = []
    def info(fmt, what, role):
        observed.append((fmt, what, role))
        return fixtures.runtimes_json().decode()
    installer._info_field = info
    assert installer._runtime_mapping('rollback') == json.loads(fixtures.runtimes_json())
    assert observed == [(TEMPLATE, 'runtimes', 'rollback')]


def test_empty_runtime_projection_refuses_before_use():
    installer = mod.InstallEngine.__new__(mod.InstallEngine)
    installer._info_field = lambda *_: '{  }'
    with pytest.raises(mod.InstallError, match='DOCKER_FACT_UNPARSEABLE'):
        installer._runtime_mapping()


@pytest.mark.parametrize('field,value', [
    ('path', 'changed'), ('runtimeArgs', ['--different']),
    ('runtimeType', 'io.containerd.changed.v2'), ('options', {'BinaryName': 'changed'}),
])
def test_non_target_configuration_change_still_blocks_settlement(field, value):
    installer = mod.InstallEngine.__new__(mod.InstallEngine)
    baseline = {'runc': {'path': 'runc'}, 'shim': {
        'runtimeType': 'io.containerd.example.v2', 'options': {'BinaryName': 'original'}}}
    installer.runtime_mapping_before = baseline
    installer.default_runtime_before = 'runc'
    current = copy.deepcopy(baseline)
    current['runc'][field] = value
    state = {'service': {'ActiveState': 'active'}, 'default': 'runc', 'runtimes': current}
    assert not installer._state_verified(state, expect_rf=False)
    state['runtimes'] = baseline
    assert installer._state_verified(state, expect_rf=False)


class API(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        path = re.sub(r'^/v[0-9]+\.[0-9]+', '', self.path)
        self.server.requests.append(path)
        if path not in {'/_ping', '/info'}:
            self.send_error(404)
            return
        body = (b'OK' if path == '/_ping' else
                json.dumps({'ID': 'synthetic-only', 'Runtimes': self.server.runtimes}).encode())
        self.send_response(200)
        self.send_header('Api-Version', '1.52')
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    do_HEAD = do_GET


def test_actual_cli_projects_large_status_without_losing_configuration(record_property):
    cli = os.environ.get('RF_TEST_DOCKER_CLI')
    if not cli:
        pytest.skip('opt-in CLI against owned synthetic Unix API only')
    assert Path(cli).is_absolute() and Path(cli).is_file()
    # Keep the socket below the portable sockaddr_un length limit. This is a
    # disposable test fixture, not an implementation checkout.
    with tempfile.TemporaryDirectory(prefix='rf-rt-', dir='/tmp') as tmp:
        base = Path(tmp)
        (base / 'config').mkdir(mode=0o700)
        (base / 'home').mkdir(mode=0o700)
        (base / 'config/config.json').write_text('{"auths":{}}')
        os.chmod(base / 'config/config.json', 0o600)
        env = {'PATH': '/nonexistent', 'HOME': str(base / 'home'),
               'LANG': 'C', 'LC_ALL': 'C', 'DOCKER_API_VERSION': '1.52'}
        version = subprocess.run([cli, '--version'], env=env, capture_output=True,
                                 timeout=5, check=True).stdout.decode().strip()
        record_property('actual_client_version', version)
        runtimes = {
            'runc': {'path': 'runc', 'status': {'org.opencontainers.runtime-spec.features': 'x' * 20000}},
            'shim': {'runtimeType': 'io.containerd.example.v2',
                     'options': {'BinaryName': 'original', 'nested': {'value': True}}},
            'rf-runsc': {'path': '/synthetic/runsc', 'runtimeArgs': ['--network=none']},
            'escaped"name': {'path': '/synthetic/path with spaces'},
        }
        sock = str(base / 'api.sock')
        with socketserver.UnixStreamServer(sock, API) as server:
            os.chmod(sock, 0o600)
            server.runtimes, server.requests = runtimes, []
            thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .02})
            thread.start()
            try:
                def run(fmt):
                    result = subprocess.run([cli, '--host', 'unix://' + sock,
                        '--config', str(base / 'config'), 'info', '--format', fmt],
                        env=env, capture_output=True, timeout=10, check=True)
                    assert not result.stderr
                    return result.stdout
                legacy = run('{{json .Runtimes}}')
                assert len(legacy) > 8192
                installer = mod.InstallEngine.__new__(mod.InstallEngine)
                installer._info_field = lambda fmt, what, role: run(fmt).decode()
                projected = installer._runtime_mapping()
                expected = {name: {key: value for key, value in config.items() if key != 'status'}
                            for name, config in runtimes.items()}
                assert projected == expected
                assert len(json.dumps(projected).encode()) < 1024
                # Both a nil and an empty daemon map render as an empty JSON
                # object under the projection. Neither is a usable runtime fact.
                for missing in (None, {}):
                    server.runtimes = missing
                    with pytest.raises(mod.InstallError, match='DOCKER_FACT_UNPARSEABLE'):
                        installer._runtime_mapping()
                assert server.requests.count('/info') == 4
                assert set(server.requests) <= {'/_ping', '/info'} and len(server.requests) <= 8
                record_property('legacy_output_bytes', len(legacy))
                record_property('projected_configuration_bytes', len(json.dumps(projected).encode()))
            finally:
                server.shutdown()
                thread.join(timeout=2)
                assert not thread.is_alive()
