"""Pure source guards only; no CLI, subprocess, API server or socket starts."""
import base64
import io
import json
from types import SimpleNamespace
import pytest
import cli29_anonymous_config as source


def test_closed_owned_helper_path_and_env():
    env = source.client_env('/owned/helpers', '/owned/empty-home', '/owned/helper.log')
    assert env['PATH'] == '/owned/helpers'
    assert env['HOME'] == '/owned/empty-home'
    assert set(env) == {'PATH', 'HOME', 'LANG', 'LC_ALL', 'RF_FAKE_HELPER_LOG'}
    assert not any(k.startswith('DOCKER') for k in env)


def test_exact_anonymous_bytes_and_both_global_bindings():
    assert json.loads(source.ANON) == {'auths': {'https://index.docker.io/v1/': {}}}
    assert source.client_argv('/owned/config', 'unix:///owned/api.sock', 'image', 'pull', source.IMAGE) == [
        '/usr/bin/docker', '--host', 'unix:///owned/api.sock', '--config', '/owned/config',
        'image', 'pull', source.IMAGE]


def fake_request(path, auth):
    response = []
    obj = SimpleNamespace(path=path, command='POST', server=SimpleNamespace(rows=[]),
        headers={'X-Registry-Auth': base64.urlsafe_b64encode(json.dumps(auth).encode()).decode()},
        send_response=lambda code: response.append(code), send_header=lambda *args: None,
        end_headers=lambda: None, wfile=io.BytesIO(), close_connection=False)
    source.FakeAPI.serve(obj)
    return response, obj.server.rows


def test_fake_api_accepts_only_exact_mock_image_and_anonymous_auth():
    response, rows = fake_request('/v1.52/images/create?fromImage=docker.io%2Flibrary%2Fpython&tag=sha256%3A'+source.DIGEST,
                                  {'serveraddress': 'https://index.docker.io/v1/'})
    assert response == [200]
    assert rows == [{'method': 'POST', 'path': '/images/create', 'anonymous_auth': True, 'accepted': True}]


@pytest.mark.parametrize('auth', [{'username': 'synthetic'}, {'password': 'synthetic'},
                                   {'identitytoken': 'synthetic'}, {'unexpected': ''}])
def test_fake_api_refuses_any_auth_identity_or_unreviewed_fields(auth):
    response, rows = fake_request('/images/create?fromImage=python&tag=sha256%3A'+source.DIGEST, auth)
    assert response == [400]
    assert rows[0]['accepted'] is False


@pytest.mark.parametrize('path', ['/images/create?fromImage=other&tag=sha256%3A'+source.DIGEST,
                                  '/containers/create', '/images/create?fromImage=python&tag=latest'])
def test_fake_api_refuses_unrelated_endpoints_or_images(path):
    response, rows = fake_request(path, {})
    assert response == [400]
    assert rows[0]['accepted'] is False
