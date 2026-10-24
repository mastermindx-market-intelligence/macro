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
