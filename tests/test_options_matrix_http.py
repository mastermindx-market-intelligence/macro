"""Real native authorization composition with synthetic captures; no live I/O."""
import dataclasses
import hashlib
import json

import pytest

from app.options_matrix_http import matrix_display_response
from tests import test_options_matrix_delivery as D
from tests.test_options_matrix_delivery import native
from tests.test_options_auth import env
from tests import test_options_auth as Auth
from tests import test_options_selection_composition as F


def respond(x, src, **changes):
    kw = {k: v for k, v in x['f']['kwargs'].items() if k != 'decision_at'}
    kw.update(access_token=Auth.token(), source=src, clock=lambda: F.NOW)
    kw.update(changes)
    return matrix_display_response(x['ref'], x['matrix'], x['selected'], **kw)


def test_exact_http_bytes_and_fresh_authorization(native, tmp_path, env):
    src = D.source(native, tmp_path)
    response = respond(native, src)
    assert response.status_code == 200
    assert response.body is native['raw']
    assert hashlib.sha256(response.body).hexdigest() == native['ref'].sha256
    assert response.headers['content-length'] == str(len(native['raw']))
    assert response.headers['content-type'] == 'application/json'
    assert response.headers['cache-control'] == 'private, no-store'
    assert response.headers['vary'] == 'Authorization, Cookie'
    assert json.dumps(json.loads(response.body)).encode() != response.body
    assert env.auth_calls == 2 and env.store_calls == 1
    assert respond(native, src).body == response.body
    assert env.auth_calls == 4 and env.store_calls == 2


@pytest.mark.parametrize('failure', ['source', 'binding', 'bytes', 'selection', 'entitlement', 'policy'])
def test_no_data_on_refusal(native, tmp_path, env, failure):
    src = D.source(native, tmp_path)
    if failure == 'source': src = None
    if failure == 'binding': src = dataclasses.replace(src, binding=None)
    if failure == 'bytes':
        native['matrix'] = dataclasses.replace(native['matrix'], body=native['raw'] + b' ')
    if failure == 'selection': native['selected'] = b'{}'
    if failure == 'entitlement': env.row = {'tier': 'free', 'features': []}
    if failure == 'policy': src = dataclasses.replace(src, evidence_sha256='0' * 64)
    response = respond(native, src)
    assert response.status_code == 503
    assert json.loads(response.body) == {'error': 'matrix_display_unavailable'}
    assert response.body != native['raw']
    assert response.headers['cache-control'] == 'private, no-store'
    if failure in ('source', 'binding', 'bytes'):
        assert env.auth_calls == 0 and env.store_calls == 0


def test_unexpected_reader_error_has_no_data_or_secret(native, tmp_path, env, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError('SECRET TOKEN AND PRIVATE SOURCE DETAILS')
    monkeypatch.setattr('app.options_matrix_http.resolve_authenticated_matrix_display', broken)
    response = respond(native, D.source(native, tmp_path))
    assert response.status_code == 503
    assert b'SECRET' not in response.body

# Exercise the real router through the exact incumbent registration statements,
# without starting unrelated application services or replacing the route handler.
def registered_app():
    import ast
    from pathlib import Path
    from fastapi import FastAPI
    tree = ast.parse(Path('app/main.py').read_text())
    nodes = [node for node in tree.body if
             (isinstance(node, ast.ImportFrom) and node.module == 'app.options_matrix_http')
             or (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                 and isinstance(node.value.func, ast.Attribute)
                 and node.value.func.attr == 'include_router'
                 and any(isinstance(a, ast.Name) and a.id == 'options_matrix_display_router'
                         for a in node.value.args))]
    assert len(nodes) == 2
    app = FastAPI()
    exec(compile(ast.Module(body=nodes, type_ignores=[]), 'app/main.py', 'exec'), {'app': app})
    return app


def configured_client(x, tmp_path, env, *, configured=True):
    from fastapi.testclient import TestClient
    from app import options_matrix_http as H
    app = registered_app()
    calls = []
    if configured:
        def capture(ref):
            assert env.auth_calls >= 1  # real pre-capture Auth has completed
            assert ref == x['ref']
            calls.append(ref)
            kw = x['f']['kwargs']
            return H.MatrixHTTPInputs(x['matrix'], kw['aliases'], kw['security_master'],
                                      kw['root_evidence'], D.source(x, tmp_path))
        app.state.options_matrix_display_runtime = H.MatrixHTTPRuntime(capture, lambda: F.NOW)
    return TestClient(app), calls


def route_url(x):
    from urllib.parse import urlencode
    return '/api/options/matrix/display/SPY?' + urlencode({
        'version_ref': x['ref'].version_ref, 'fingerprint': x['ref'].sha256})


def route_headers(**changes):
    return {'Authorization': 'Bearer '+Auth.token(), 'Content-Type': 'application/octet-stream', **changes}


def test_registered_asgi_request_reads_native_after_auth_and_returns_exact(native, tmp_path, env):
    client, calls = configured_client(native, tmp_path, env)
    for n in (1, 2):
        response = client.post(route_url(native), content=native['selected'], headers=route_headers())
        assert response.status_code == 200 and response.content == native['raw']
        assert response.headers['cache-control'] == 'private, no-store'
        assert len(calls) == n and env.auth_calls == n*3 and env.store_calls == n


@pytest.mark.parametrize('token', ['invalid', Auth.token(role='anon'), Auth.token(sub=Auth.SID)])
def test_registered_bad_auth_never_captures(native, tmp_path, env, token):
    client, calls = configured_client(native, tmp_path, env)
    response = client.post(route_url(native), content=native['selected'],
                           headers=route_headers(Authorization='Bearer '+token))
    assert response.status_code == 503 and calls == []
    assert response.content != native['raw']


def test_registered_missing_native_runtime_is_unavailable(native, tmp_path, env):
    client, calls = configured_client(native, tmp_path, env, configured=False)
    response = client.post(route_url(native), content=native['selected'], headers=route_headers())
    assert response.status_code == 503 and calls == [] and env.auth_calls == 1
    assert response.headers['cache-control'] == 'private, no-store'


@pytest.mark.parametrize('change', ['policy', 'vendor', 'duplicate_ref', 'duplicate_auth', 'encoding', 'oversize', 'empty', 'bad_type'])
def test_registered_boundary_rejects_browser_authority_and_ambiguity(native, tmp_path, env, change):
    client, calls = configured_client(native, tmp_path, env)
    url, body, headers = route_url(native), native['selected'], route_headers()
    expected = 400
    if change in ('policy', 'vendor'): url += '&'+change+'=browser-cannot-grant'
    if change == 'duplicate_ref': url += '&fingerprint='+native['ref'].sha256
    if change == 'duplicate_auth':
        headers = list(headers.items())+[('Authorization', 'Bearer '+Auth.token())]; expected = 401
    if change == 'encoding': headers['Content-Encoding'] = 'gzip'; expected = 415
    if change == 'bad_type': headers['Content-Type'] = 'application/json'; expected = 415
    if change == 'oversize': body = b' '*2049
    if change == 'empty': body = b''
    response = client.post(url, content=body, headers=headers)
    assert response.status_code == expected and calls == []
    assert response.headers['cache-control'] == 'private, no-store'
    assert env.auth_calls == 0


def test_registered_forged_selection_cannot_grant(native, tmp_path, env):
    client, calls = configured_client(native, tmp_path, env)
    response = client.post(route_url(native), content=b'{"policy":"grant","dataset":"invented"}', headers=route_headers())
    assert response.status_code == 503 and len(calls) == 1
    assert response.content != native['raw']


def test_registered_get_cannot_release_or_capture(native, tmp_path, env):
    client, calls = configured_client(native, tmp_path, env)
    response = client.get(route_url(native), headers=route_headers())
    assert response.status_code == 405 and response.headers['allow'] == 'POST'
    assert response.headers['cache-control'] == 'private, no-store'
    assert calls == [] and env.auth_calls == 0


def test_registered_source_body_corruption_cannot_release(native, tmp_path, env):
    native['matrix'] = dataclasses.replace(native['matrix'], body=native['raw']+b' ')
    client, calls = configured_client(native, tmp_path, env)
    response = client.post(route_url(native), content=native['selected'], headers=route_headers())
    assert response.status_code == 503 and len(calls) == 1
    assert response.content != native['raw']


def test_registered_response_deadline_drops_late_thread_result(native, tmp_path, env, monkeypatch):
    import time
    from app import options_matrix_http as H
    client, calls = configured_client(native, tmp_path, env)
    def late(*args):
        time.sleep(0.03)
        return H.Response(content=native['raw'])
    monkeypatch.setattr(H, '_serve', late)
    monkeypatch.setattr(H, '_RESPONSE_TIMEOUT', 0.001)
    response = client.post(route_url(native), content=native['selected'], headers=route_headers())
    assert response.status_code == 503 and response.content != native['raw']


def test_registered_body_deadline_and_disconnect_never_capture(native, tmp_path, env, monkeypatch):
    import asyncio
    from app import options_matrix_http as H
    from starlette.requests import ClientDisconnect
    client, calls = configured_client(native, tmp_path, env)
    async def stalled(request):
        await asyncio.sleep(0.03)
        return native['selected']
    monkeypatch.setattr(H, '_selection_body', stalled)
    monkeypatch.setattr(H, '_BODY_TIMEOUT', 0.001)
    response = client.post(route_url(native), content=native['selected'], headers=route_headers())
    assert response.status_code == 503 and calls == [] and env.auth_calls == 0
    async def disconnected(request):
        raise ClientDisconnect()
    monkeypatch.setattr(H, '_selection_body', disconnected)
    response = client.post(route_url(native), content=native['selected'], headers=route_headers())
    assert response.status_code == 503 and calls == [] and env.auth_calls == 0


def test_asgi_wire_fixture_for_actual_next_transport(native, tmp_path, env):
    import base64
    client, _ = configured_client(native, tmp_path, env)
    response = client.post(route_url(native), content=native['selected'], headers=route_headers())
    assert response.status_code == 200
    fixture = {'provenance': 'SYNTHETIC native helper through incumbent ASGI registration',
               'matrix_base64': base64.b64encode(response.content).decode(),
               'selection_base64': base64.b64encode(native['selected']).decode(),
               'root': native['ref'].root, 'fingerprint': native['ref'].sha256,
               'version_ref': native['ref'].version_ref}
    (tmp_path / 'matrixDisplayASGIWire.json').write_text(json.dumps(fixture, indent=2)+'\n')


def test_missing_lazy_auth_dependency_refuses_before_capture(monkeypatch):
    import builtins
    from app import options_matrix_http as H
    original = builtins.__import__
    captured = []

    def unavailable(name, *args, **kwargs):
        if name == 'app.options_auth':
            raise ModuleNotFoundError('private dependency detail')
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', unavailable)
    runtime = H.MatrixHTTPRuntime(lambda ref: captured.append(ref))
    response = H._serve(runtime, None, b'{}', 'secret-token')
    assert response.status_code == 503
    assert response.body == b'{"error":"matrix_display_unavailable"}'
    assert response.headers['cache-control'] == 'private, no-store'
    assert captured == []
