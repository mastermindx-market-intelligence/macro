"""Versioned processor scope, synthetic pinned policy only; no runtime grant."""
from dataclasses import asdict, replace

import pytest

from engine.intelligence_workspace import options_source_use as M
from tests import test_options_source_use as P

DEST = M.ProcessorDestination('synthetic', 'https://processor.invalid/v1/messages', 'model-1')


def record():
    r = P.policy_record()
    r['schema'] = 'options.source_use.question/v2'
    r['actions'] = {'export': dict(r['actions']['export'], channel='/api/brain/chat',
        recipients=['authenticated_customer', 'external_processor'], processor=asdict(DEST))}
    return r


def backend(tmp_path, r=None, dest=DEST):
    return P.make_backend(tmp_path, record=r or record(),
        resolver=P.fresh_resolver(channel='/api/brain/chat',
            recipients=('authenticated_customer', 'external_processor'), processor=dest))


def test_exact_processor_policy(tmp_path):
    b = backend(tmp_path)
    assert b.decision(P.make_request(action='export'))['status'] == 'allowed'


@pytest.mark.parametrize('field,value', [
    ('provider', 'other'), ('endpoint', 'https://other.invalid/v1/messages'), ('model', 'other'),
])
def test_wrong_actual_processor_refuses(tmp_path, field, value):
    with pytest.raises(M.SourceUseRefused):
        backend(tmp_path, dest=replace(DEST, **{field: value})).decision(P.make_request(action='export'))


@pytest.mark.parametrize('mutation', ['v1', 'unknown_version', 'display', 'extra', 'no_processor',
    'internal', 'wildcard', 'http', 'userinfo', 'query', 'fragment', 'unknown', 'revoked', 'expired', 'unhashable_recipient'])
def test_no_implicit_processor_grants(tmp_path, mutation):
    r = record(); a = r['actions']['export']
    if mutation == 'v1': r.pop('schema')
    if mutation == 'unknown_version': r['schema'] = 'options.source_use.question/v3'
    if mutation == 'display': r['actions'] = {'display': a}
    if mutation == 'extra': a['processor']['token'] = 'synthetic-not-secret'
    if mutation == 'no_processor': a.pop('processor')
    if mutation == 'unhashable_recipient': a['recipients'] = [{}]
    if mutation == 'internal': a['recipients'] = ['internal_customer']
    if mutation == 'wildcard': a['processor']['provider'] = '*'
    if mutation == 'http': a['processor']['endpoint'] = 'http://processor.invalid'
    if mutation == 'userinfo': a['processor']['endpoint'] = 'https://user@processor.invalid'
    if mutation == 'query': a['processor']['endpoint'] += '?key=synthetic'
    if mutation == 'fragment': a['processor']['endpoint'] += '#fragment'
    if mutation == 'unknown': a['processor']['model'] = 'unknown'
    if mutation == 'revoked': r['state'] = 'revoked'
    if mutation == 'expired': r['effective_until'] = '2026-10-02T00:00:00Z'
    with pytest.raises(M.SourceUseRefused): backend(tmp_path, r).decision(P.make_request(action='export'))


def test_v1_display_unchanged(tmp_path):
    assert P.make_backend(tmp_path).decision(P.make_request())['status'] == 'allowed'
