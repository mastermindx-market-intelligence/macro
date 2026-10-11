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


@pytest.fixture
def selection_boundary(boundary, sample):
    from copy import deepcopy
    from engine.company_intelligence import issuer_disclosure_selection as s
    body, edition, fact, _, authority, _ = sample
    edition, fact = deepcopy(edition), deepcopy(fact)
    issuer = 'ISS:US-XNAS-TEST'
    edition['issuer_id'] = issuer
    did = native.disclosure_id(issuer, edition['source_key'])
    edition['disclosure_id'] = did
    fact.update(subject_id=issuer, disclosure_id=did, edition=native.validate_edition(edition).payload(),
                fact_id=native.fact_id(did, fact['claim_key']))
    req = native.Request(fact['fact_id'], api.PURPOSE, api.AUDIENCE)
    authority.admission = replace(authority.admission, request=req, reference=native.validate_fact(fact),
                                  edition=native.validate_edition(edition),
                                  allowed_fields=authority.admission.allowed_fields | {'subject_id'},
                                  subject_binding=native.SubjectIdentityBinding(
                                      issuer, '0000000001', 'synthetic.issuer_snapshot/v1',
                                      '9'*64, 200, fact['subject_identity']))
    native.publish_disclosure(boundary[5], authority, req, edition=edition, fact=fact,
                              source_reader=SyntheticSourceReader(body))
    entry = s.SelectionEntry(fact['fact_id'], native.validate_fact(fact), native.validate_edition(edition))
    snapshot = s.IssuerSelection(issuer, '0000000001', 'synthetic.issuer_snapshot/v1', '9'*64, 200, authority.admission.generation,
                                api.PURPOSE, api.AUDIENCE, (entry,))
    class Owner:
        value = snapshot
        calls = 0
        change_at = None
        def resolve_issuer(self, *args):
            self.calls += 1
            return replace(self.value, generation='changed') if self.change_at == self.calls else self.value
    owner = Owner()
    app = boundary[0].app
    old = app.state.company_disclosure_reader
    app.state.company_disclosure_reader = replace(old, selection_owner=owner)
    url = '/api/company-intelligence/private/issuers/' + issuer + '/product-integrations'
    boundary[3].clear(); authority.calls = 0
    return boundary, owner, url


def selection_get(selection_boundary, query='', headers=None):
    boundary, _, url = selection_boundary
    return boundary[0].get(url+query, headers={'Authorization': 'Bearer synthetic-token'} if headers is None else headers)


def test_selection_is_exact_same_issuer_artifact_and_generation(selection_boundary):
    boundary, owner, _ = selection_boundary
    response = selection_get(selection_boundary)
    assert response.status_code == 200, response.text
    private_headers(response)
    value = response.json()
    assert value['issuer_binding']['issuer_id'] == owner.value.issuer_id
    assert value['issuer_role'] == 'subject_disclosing_company'
    chosen = value['selections'][0]
    fact = boundary[0].get('/api/company-intelligence/private/product-integrations/'+chosen['fact_id'],
                          headers={'Authorization': 'Bearer synthetic-token'}).json()
    assert (chosen['fact_reference'], chosen['edition_reference'], value['generation']) == (fact['reference'], fact['edition'], fact['generation'])
    assert 'product' not in chosen and 'purpose' not in value


@pytest.mark.parametrize('change', ['generation', 'purpose', 'audience', 'issuer', 'duplicates', 'overflow', 'reference', 'cik', 'missing'])
def test_invalid_owner_selection_never_constructs_private_store(selection_boundary, change):
    boundary, owner, _ = selection_boundary
    s = owner.value; entry=s.selections[0]
    kwargs = {'generation': {'generation':'different'}, 'purpose': {'purpose':'different'},
              'audience': {'audience':'different'}, 'issuer': {'issuer_id':'ISS:US-XNAS-OTHER'},
              'duplicates': {'selections': (entry,entry)}, 'overflow': {'selections': (entry,)*17},
              'reference': {'selections': (replace(entry, fact_reference=replace(entry.fact_reference, sha256='e'*64)),)},
              'cik': {'evidenced_cik':'0'}}
    owner.value = None if change == 'missing' else replace(s, **kwargs[change])
    response=selection_get(selection_boundary)
    assert response.status_code == 503
    assert 'private_store' not in boundary[3]


def test_selection_requires_feature_before_owner(selection_boundary):
    boundary, owner, _ = selection_boundary
    boundary[2]['features']=[]
    assert selection_get(selection_boundary).status_code == 403 and owner.calls == 0
    assert 'private_store' not in boundary[3]


def test_qualified_empty_generation_is_distinct_from_unavailable(selection_boundary):
    boundary, owner, _ = selection_boundary
    owner.value=replace(owner.value, selections=())
    r=selection_get(selection_boundary)
    assert r.status_code==200 and r.json()['selections']==[]
    assert 'private_store' not in boundary[3]
    owner.value=None
    assert selection_get(selection_boundary).status_code==503


def test_no_counterparty_listing_under_subject_contract(selection_boundary):
    boundary, owner, url = selection_boundary
    wrong='ISS:US-XNAS-OTHER'
    owner.value=replace(owner.value,issuer_id=wrong)
    r=boundary[0].get(url.replace('ISS:US-XNAS-TEST',wrong), headers={'Authorization':'Bearer synthetic-token'})
    assert r.status_code==503


def test_selection_changed_after_read_refuses_whole_composition(selection_boundary):
    _, owner, _=selection_boundary
    owner.change_at=2
    assert selection_get(selection_boundary).status_code==503


def test_final_authority_recheck_covers_selection_serialization(selection_boundary):
    boundary, _, _=selection_boundary
    boundary[4].change_at=4
    assert selection_get(selection_boundary).status_code==503


@pytest.mark.parametrize('query',['?ticker=TEST','?cik=0000000001','?generation=old','?as_of=2020-01-01'])
def test_selection_cannot_choose_identity_or_old_generation(selection_boundary,query):
    boundary,owner,_=selection_boundary
    assert selection_get(selection_boundary,query).status_code==400 and owner.calls==0
    assert 'private_store' not in boundary[3]


@pytest.mark.parametrize('changed', [{'evidenced_cik':'0000000099'}, {'identity_snapshot_sha256':'e'*64},
    {'identity_snapshot_schema':'other.snapshot/v1'}, {'identity_snapshot_byte_length':201}])
def test_selection_identity_must_match_fact_admission_before_private_io(selection_boundary,changed):
    boundary,owner,_=selection_boundary
    owner.value=replace(owner.value,**changed)
    response=selection_get(selection_boundary)
    assert response.status_code==503
    assert 'private_store' not in boundary[3]


def test_missing_subject_binding_refuses_before_private_store(selection_boundary):
    boundary, _, _ = selection_boundary
    boundary[4].admission = replace(boundary[4].admission, subject_binding=None)
    assert selection_get(selection_boundary).status_code == 503
    assert 'private_store' not in boundary[3]


def test_matching_snapshot_cannot_hide_wrong_fact_identity_decision(selection_boundary):
    boundary, _, _ = selection_boundary
    a = boundary[4].admission
    boundary[4].admission = replace(a, subject_binding=replace(a.subject_binding, decision_revision='a'*64))
    response = selection_get(selection_boundary)
    assert response.status_code == 503
    assert 'private_store' in boundary[3]  # Exact content read is needed to falsify the owner decision.
    assert 'fact' not in response.json()
