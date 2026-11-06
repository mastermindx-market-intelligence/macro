"""Actual temporary trusted owner through the authenticated saved-output route."""
from __future__ import annotations
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app import market_memory as api
from engine.neuralweb import market_memory_retained_saved as saved
from engine.neuralweb import market_memory_retained_use as use
from tests.test_market_memory_retained_saved import env, _rewrite_registration

@pytest.fixture
def client(env, monkeypatch):
    monkeypatch.setattr(api, '_repo_root', lambda: env.root)
    api._reset_symbol_rate_limit_for_tests()
    app = FastAPI(); app.include_router(api.router)
    app.dependency_overrides[api.require_site_full_user] = lambda: {'id':'member'}
    with TestClient(app) as value:
        yield value
    api._reset_symbol_rate_limit_for_tests()


def query(env):
    return {key:value for key,value in env.spec.items() if key != 'user_id'}


def test_http_original_output_exact_packet_and_private_headers(client, env):
    response = client.get('/api/market-memory/v1/macro/retained/saved', params=query(env))
    assert response.status_code == 200, response.text
    assert response.json()['context'] == env.query.packet
    assert response.json()['capture_receipt'] == env.query.capture_receipt
    assert response.json()['mode'] == 'retained_actual_output'
    assert 'no-store' in response.headers['cache-control']
    assert response.headers['etag'] == '"'+env.query.capture_receipt['packet_sha256']+'"'

@pytest.mark.parametrize('change', ['missing','unknown','duplicate','bad_id','bad_cutoff'])
def test_malformed_saved_request_before_private_reader(client, env, monkeypatch, change):
    q=query(env)
    if change=='missing':q.pop('capture_id')
    elif change=='unknown':q['mode']='current'
    elif change=='bad_id':q['context_id']='wrong'
    elif change=='bad_cutoff':q['query_cutoff']='2026-02-30T00:00:00Z'
    else:q=list(q.items())+[('context_id',q['context_id'])]
    monkeypatch.setattr(saved.trusted.TrustedFileAsKnownAtReader,'observe_generation_head',
                        lambda *a,**k:pytest.fail('malformed request read private owner'))
    response=client.get('/api/market-memory/v1/macro/retained/saved',params=q)
    assert response.status_code==400


def test_source_denial_is_typed_no_private_output(client,env):
    _rewrite_registration(env.root,lambda value:value.update(enabled=False))
    response=client.get('/api/market-memory/v1/macro/retained/saved',params=query(env))
    assert response.status_code==403
    assert response.json()=={'detail':{'state':'SOURCE_USE_NOT_ADMITTED'}}


def test_unsupported_clock_is_distinct_from_missing_exact_capture(client,env):
    q=query(env);q['query_cutoff']='2026-08-01T00:00:00Z'
    assert client.get('/api/market-memory/v1/macro/retained/saved',params=q).status_code==422
    q=query(env);q['capture_id']='mmcapture_'+'f'*64
    assert client.get('/api/market-memory/v1/macro/retained/saved',params=q).status_code==404


def test_saved_request_shared_user_rate_and_busy_slot(client,env):
    q=query(env)
    for _ in range(api._PLAYBACK_USER_LIMIT):
        assert client.get('/api/market-memory/v1/macro/retained/saved',params=q).status_code==200
    assert client.get('/api/market-memory/v1/macro/retained/saved',params=q).status_code==429
    api._reset_symbol_rate_limit_for_tests()
    assert api._playback_slots.acquire(False);assert api._playback_slots.acquire(False)
    try:
        response=client.get('/api/market-memory/v1/macro/retained/saved',params=q)
        assert response.status_code==503 and response.json()['detail']['state']=='BUSY'
    finally:
        api._playback_slots.release();api._playback_slots.release()
