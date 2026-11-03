"""Original trusted owners and real policy prove legacy-route source admission."""
import json
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app import market_memory as api
from engine.neuralweb import market_memory_pit as pit
from engine.neuralweb import market_memory_trusted as trusted
from engine.neuralweb import market_memory_playback as playback
from engine.neuralweb import market_memory_retained_use as use
from engine.neuralweb import market_memory_retained_legacy_guard as guard
from scripts.initialize_market_memory_w1a import initialize_w1a_store
from tests.test_market_memory_retained_saved import env, _rewrite_registration
from tests.test_market_memory_pit import _packet, _fixed_clock

@pytest.fixture
def composite(env):
    w1a=env.root/'w1a';initialize_w1a_store(w1a)
    return trusted.CompositeAsKnownAtReader(w1a,env.reader.root)

def wrap(env,composite):
    return guard.guard_trusted_legacy_reader(composite,root=env.root,user_id='member')


def test_allowed_exact_context_and_query_keep_original_packet(env,composite):
    owner=composite.trusted; w1a=composite.w1a
    with wrap(env,composite) as g:
        assert composite.read_stored_context_id(env.spec['context_id']).packet==env.query.packet
        clocks=env.query.packet['clocks']
        assert composite.read_stored_as_known_at(subject=env.query.packet['subject'],event_time=clocks['event_time'],as_known_at=clocks['as_known_at']).packet==env.query.packet
        g.final_authorize();assert composite.w1a is w1a
    assert composite.trusted is owner
    with pytest.raises(PermissionError):g.final_authorize()

@pytest.mark.parametrize('scope',['capture','source','disabled'])
def test_denied_before_original_payload_and_never_w1a_fallback(env,composite,monkeypatch,scope):
    if scope=='capture':change=lambda v:v.update(revoked_capture_ids=[env.spec['capture_id']])
    elif scope=='source':change=lambda v:v.update(revoked_source_receipt_ids=env.query.capture_receipt['source_receipt_ids'])
    else:change=lambda v:v.update(enabled=False)
    _rewrite_registration(env.root,change)
    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader,'read_stored_from_pinned_generation',lambda *a,**k:pytest.fail('private packet read after denied source'))
    monkeypatch.setattr(composite.w1a,'read_stored_context_id',lambda *a,**k:pytest.fail('trusted denial fell through to W1A'))
    with wrap(env,composite):
        with pytest.raises(PermissionError):composite.read_stored_context_id(env.spec['context_id'])

@pytest.mark.parametrize('scope',['source','registration','user'])
def test_final_revocation_rechecks_all_touched_originals(env,composite,monkeypatch,scope):
    with wrap(env,composite) as g:
        returned=composite.read_stored_context_id(env.spec['context_id'])
        returned.packet['context_id']='mutated_return_does_not_grant_authority'
        if scope=='source':_rewrite_registration(env.root,lambda v:v.update(revoked_source_receipt_ids=env.query.capture_receipt['source_receipt_ids']))
        elif scope=='registration':_rewrite_registration(env.root,lambda v:v.update(enabled=False))
        else:monkeypatch.setattr(use,'_enforce_current_site_user',lambda *a:(_ for _ in ()).throw(use.RetainedUseError('revoked')))
        with pytest.raises(PermissionError):g.final_authorize()


def test_unreturned_catalog_row_revocation_refuses_whole_response(env,composite):
    _rewrite_registration(env.root,lambda v:v.update(revoked_capture_ids=[env.old.capture_receipt['capture_id']]))
    with wrap(env,composite):
        with pytest.raises(PermissionError):
            playback.read_operational_playback_catalog(reader=composite,subject=env.query.packet['subject'],offset=0,limit=1)


def test_proven_trusted_miss_keeps_w1a_even_without_house_registration(env,composite,monkeypatch):
    _fixed_clock(monkeypatch);original=pit.capture_context(composite.w1a.root,_packet())
    (env.root/use.REGISTRATION).unlink()
    with wrap(env,composite) as g:
        assert composite.read_stored_context_id(original.packet['context_id']).packet==original.packet
        g.final_authorize()


def test_missing_corrupt_trusted_store_does_not_become_exact_miss(env,composite,monkeypatch):
    monkeypatch.setattr(composite.trusted,'observe_generation_head',lambda **k:(_ for _ in ()).throw(pit.MarketMemoryStoreError('corrupt')))
    with wrap(env,composite):
        with pytest.raises(pit.MarketMemoryStoreError):composite.read_stored_context_id(env.spec['context_id'])


def test_public_proxy_cannot_disclose_full_feature_or_read_outside_guard(env,composite):
    with wrap(env,composite):
        proxy=composite.trusted
        with pytest.raises(PermissionError):proxy.read_macro_feature_from_pinned_generation(env.pin,query_id=env.spec['query_id'])
        with pytest.raises(PermissionError):proxy.read_pinned_capture_projections(env.pin)
    with pytest.raises(PermissionError):proxy.read_pinned_generation()


def test_one_aggregate_budget_covers_owner_request(env,composite,monkeypatch):
    monkeypatch.setattr(guard.cohort,'MAX_OWNER_BYTES',1)
    with wrap(env,composite):
        with pytest.raises(pit.OwnerReadBudgetError):composite.read_stored_context_id(env.spec['context_id'])


def test_all_three_http_routes_enforce_actual_source_scope(env,composite,monkeypatch):
    monkeypatch.setattr(api,'_repo_root',lambda:env.root)
    monkeypatch.setattr(api,'_pit_reader',lambda:composite)
    api._reset_symbol_rate_limit_for_tests()
    app=FastAPI();app.include_router(api.router);app.dependency_overrides[api.require_site_full_user]=lambda:{'id':'member'}
    packet=env.query.packet;query={**packet['subject'],'event_time':packet['clocks']['event_time'],'as_known_at':packet['clocks']['as_known_at'],'mode':'operational_pit'}
    routes=[('/context/'+env.spec['context_id'],{}),('/as-known-at',query),('/playback/catalog',{**packet['subject'],'mode':playback.ACTUAL_OUTPUT_MODE,'offset':0,'limit':1})]
    with TestClient(app) as c:
        for route,q in routes:
            r=c.get('/api/market-memory/v1'+route,params=q);assert r.status_code==200,r.text
            assert 'no-store' in r.headers['cache-control']
        _rewrite_registration(env.root,lambda v:v.update(revoked_source_receipt_ids=env.query.capture_receipt['source_receipt_ids']))
        for route,q in routes:
            r=c.get('/api/market-memory/v1'+route,params=q);assert r.status_code==403,r.text
            assert r.json()=={'detail':{'state':'SOURCE_USE_NOT_ADMITTED'}}
    api._reset_symbol_rate_limit_for_tests()


def test_outer_final_check_catches_revocation_during_w1a_collision_read(env,composite,monkeypatch):
    original=composite.w1a.read_stored_context_id
    def revoke_then_read(context_id):
        _rewrite_registration(env.root,lambda v:v.update(revoked_capture_ids=[env.spec['capture_id']]))
        return original(context_id)
    monkeypatch.setattr(composite.w1a,'read_stored_context_id',revoke_then_read)
    with wrap(env,composite) as g:
        assert composite.read_stored_context_id(env.spec['context_id']).packet==env.query.packet
        with pytest.raises(PermissionError):g.final_authorize()
