"""Transport proof with synthetic identity/owner; never production admission."""
from dataclasses import replace
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app import company_disclosures as api
from engine.company_intelligence import issuer_disclosures as native
from engine.research_vault.r2_store import LocalStore
from tests.test_company_issuer_disclosures import sample, SyntheticSourceReader


@pytest.fixture
def boundary(sample, monkeypatch, tmp_path):
    from app import main, billing, paywall
    body, edition, fact, _, authority, _ = sample
    request = native.Request(fact['fact_id'], api.PURPOSE, api.AUDIENCE)
    authority.admission = replace(authority.admission, request=request)
    store = LocalStore(tmp_path / 'private')
    native.publish_disclosure(store, authority, request, edition=edition, fact=fact,
                              source_reader=SyntheticSourceReader(body))
    events = []
    def identity(token):
        events.append('authenticate')
        return SimpleNamespace(status='ok', uid='synthetic-user', record={'id': 'synthetic-user'})
    row = {'tier': 'pro', 'status': 'active', 'features': [api.FEATURE]}
    def entitlement(uid):
        assert uid == 'synthetic-user'
        events.append('entitlement')
        return row
    def factory():
        events.append('private_store')
        return store
    monkeypatch.setattr(paywall, '_resolve_identity', identity)
    monkeypatch.setattr(billing, 'read_entitlement', entitlement)
    monkeypatch.setattr(paywall, '_entitled', lambda *a: (_ for _ in ()).throw(AssertionError('other-feature cache used')))
    app = FastAPI()
    app.include_router(api.router)
    app.state.company_disclosure_reader = api.PrivateDisclosureReader(authority, factory)
    client = TestClient(app)
    url = '/api/company-intelligence/private/product-integrations/' + fact['fact_id']
    authority.calls = 0
    return client, url, row, events, authority, store, main


def get(boundary, suffix='', headers=None):
    client, url, *_ = boundary
    return client.get(url+suffix, headers={'Authorization': 'Bearer synthetic-token'} if headers is None else headers)


def private_headers(response):
    assert response.headers['cache-control'] == 'private, no-store'
    assert 'Cookie' in response.headers['vary'] and 'Authorization' in response.headers['vary']
    assert response.headers['x-robots-tag'] == 'noindex, noarchive'


def test_real_mount_and_unauthenticated_refusal_before_entitlement(boundary):
    _, url, _, events, authority, _, main = boundary
    response = TestClient(main.app).get(url)
    assert response.status_code == 401
    private_headers(response)
    assert not events and authority.calls == 0


def test_positive_uses_canonical_auth_fresh_feature_and_same_native_result(boundary):
    _, _, _, events, authority, store, _ = boundary
    before = {p.relative_to(store.root): p.read_bytes() for p in store.root.rglob('*') if p.is_file()}
    response = get(boundary)
    assert response.status_code == 200, response.text
    private_headers(response)
    assert events == ['authenticate', 'entitlement', 'private_store']
    assert authority.calls >= 3
    assert response.json() == native.read_disclosure(store, authority, authority.admission.request)
    assert before == {p.relative_to(store.root): p.read_bytes() for p in store.root.rglob('*') if p.is_file()}
    assert 'synthetic-token' not in response.text and 'text_sha256' not in response.text


@pytest.mark.parametrize('patch', [
    {'features': []}, {'features': ['site_full']}, {'features': api.FEATURE},
    {'features': [api.FEATURE, 1]}, {'tier': 'free'}, {'status': 'canceled'},
    {'status': 'past_due'}, {'tier': None}, {'status': None},
])
def test_unqualified_actual_entitlement_refuses_before_owner(boundary, patch):
    boundary[2].update(patch)
    response = get(boundary)
    assert response.status_code == 403
    private_headers(response)
    assert boundary[3] == ['authenticate', 'entitlement'] and boundary[4].calls == 0


def test_revoked_feature_not_reused_from_prior_positive(boundary):
    assert get(boundary).status_code == 200
    boundary[2]['features'] = ['site_full']
    boundary[3].clear(); boundary[4].calls = 0
    assert get(boundary).status_code == 403
    assert boundary[3] == ['authenticate', 'entitlement'] and boundary[4].calls == 0


@pytest.mark.parametrize('query', ['?purpose=public', '?audience=any', '?Admission={}',
    '?root=/private', '?mode=current&mode=historical', '?mode=historical',
    '?as_of=2026-01-01T00:00:00Z', '?mode=bad', '?mode=historical&as_of=2026-01-01',
    '?mode=historical&as_of=2026-01-01T00:00:00.0000001Z'])
def test_closed_query_controls_are_not_authority(boundary, query):
    response = get(boundary, query)
    assert response.status_code == 400
    private_headers(response)
    assert boundary[3] == ['authenticate', 'entitlement'] and boundary[4].calls == 0


def test_cookie_reaches_existing_verifier_without_second_auth_path(boundary, monkeypatch):
    main = boundary[-1]
    seen = []
    def cookie(request):
        seen.append(request.cookies.get('synthetic-session'))
        return 'synthetic-token' if seen[-1] == 'present' else None
    monkeypatch.setattr(main, '_mm_supabase_access_token', cookie)
    response = get(boundary, headers={'Cookie': 'synthetic-session=present'})
    assert response.status_code == 200 and seen == ['present']


def test_missing_owner_runtime_is_not_public_fallback(boundary):
    del boundary[0].app.state.company_disclosure_reader
    response = get(boundary)
    assert response.status_code == 503 and response.json()['code'] == 'SOURCE_RUNTIME_UNAVAILABLE'
    assert boundary[3] == ['authenticate', 'entitlement'] and boundary[4].calls == 0


def test_denied_source_never_constructs_private_store(boundary):
    boundary[4].deny = True
    response = get(boundary)
    assert response.status_code == 503 and response.json()['code'] == 'SOURCE_NOT_ADMITTED'
    assert boundary[3] == ['authenticate', 'entitlement']


def test_owner_exception_is_coarse_and_no_private_io(boundary, monkeypatch):
    monkeypatch.setattr(boundary[4], 'resolve', lambda req: (_ for _ in ()).throw(RuntimeError('private secret path')))
    response = get(boundary)
    assert response.status_code == 503 and 'secret' not in response.text
    assert boundary[3] == ['authenticate', 'entitlement']


def test_generation_change_during_private_read_refuses(boundary):
    boundary[4].change_at = 3
    response = get(boundary)
    assert response.status_code == 503
    private_headers(response)
    assert response.json()['automatic_retry_permitted'] is False


def test_unexpected_failure_also_private_and_sanitized(boundary):
    boundary[0].app.state.company_disclosure_reader = api.PrivateDisclosureReader(
        boundary[4], lambda: (_ for _ in ()).throw(RuntimeError('private secret path')))
    response = get(boundary)
    assert response.status_code == 503 and 'secret' not in response.text
    private_headers(response)
