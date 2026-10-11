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
    authority.admission = replace(authority.admission, request=request,
        subject_binding=native.SubjectIdentityBinding(fact['subject_id'], '0000000001',
            'synthetic.issuer_snapshot/v1', '9'*64, 200, fact['subject_identity']))
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
    assert response.json()['schema'] == 'company_intelligence.private_product_integration/v2'
    assert response.json()['source_timing'] == {
        'published_date': '2026-01-02', 'published_at': None,
        'publication_precision': 'date', 'known_at': '2026-01-03T10:00:00Z',
    }
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


def test_private_fact_runtime_requires_subject_binding_before_store(boundary):
    boundary[4].admission = replace(boundary[4].admission, subject_binding=None)
    response = get(boundary)
    assert response.status_code == 503
    assert 'private_store' not in boundary[3]


def test_subject_binding_revoked_during_store_construction_never_serializes(boundary):
    client, _, _, _, authority, store, _ = boundary
    def changed_factory():
        authority.admission = replace(authority.admission, subject_binding=None)
        return store
    client.app.state.company_disclosure_reader = api.PrivateDisclosureReader(authority, changed_factory)
    response = get(boundary)
    assert response.status_code == 503
    assert 'fact' not in response.json()


@pytest.mark.parametrize('route', ['fact', 'selection'])
def test_transient_binding_downgrade_cannot_skip_original_fact_decision(selection_boundary, monkeypatch, route):
    boundary, _, _ = selection_boundary
    authority = boundary[4]
    original = replace(authority.admission,
                       subject_binding=replace(authority.admission.subject_binding, decision_revision='a'*64))
    downgraded = replace(original, subject_binding=None)
    sequence = iter((original, downgraded, downgraded, original))
    monkeypatch.setattr(authority, 'resolve', lambda request: next(sequence))
    reads = []
    incumbent = boundary[5].get_bytes_strict_bounded
    def read(*args, **kwargs):
        reads.append(True)
        return incumbent(*args, **kwargs)
    monkeypatch.setattr(boundary[5], 'get_bytes_strict_bounded', read)
    if route == 'fact':
        url = '/api/company-intelligence/private/product-integrations/' + original.request.fact_id
        response = boundary[0].get(url, headers={'Authorization':'Bearer synthetic-token'})
    else:
        response = selection_get(selection_boundary)
    assert response.status_code == 503
    assert not reads

# Current company-context composition uses synthetic reference-owner evidence.
@pytest.fixture
def context_fixture(boundary):
    from datetime import date
    from io import BytesIO
    import pandas as pd
    from engine.company_intelligence import current_company_context as context
    records = {
        'security_master': [dict(security_id='SEC:US-XNAS-AAA', issuer_id='ISS:US-XNAS-AAA',
            issuer_state='RESOLVED', issuer_cik='0000000001', listing_key='US-XNAS-AAA',
            issuer_evidence_snapshot=date(2026, 1, 1), security_state=None, superseded_by=None),
            dict(security_id='SEC:US-XNAS-AAB', issuer_id='ISS:US-XNAS-AAA',
            issuer_state='RESOLVED', issuer_cik='0000000001', listing_key='US-XNAS-AAB',
            issuer_evidence_snapshot=date(2026, 1, 1), security_state=None, superseded_by=None)],
        'issuer_master': [dict(issuer_id='ISS:US-XNAS-AAA', cik='0000000001', status='active',
            evidence_source='sec_company_tickers', evidence_snapshot=date(2026, 1, 1))],
        'vendor_aliases': [dict(vendor='store', vendor_symbol=symbol, security_id='SEC:US-XNAS-'+symbol,
            valid_from=None, valid_to=None) for symbol in ['AAA', 'AAB']],
    }
    def bundle(data=records, commit='a'*40):
        blobs = {}
        for name, rows in data.items():
            output=BytesIO(); pd.DataFrame(rows).to_parquet(output, index=False); blobs[name]=output.getvalue()
        return context.IdentityBundle(commit, **blobs)
    class Owner:
        calls=0
        value=bundle()
        replacement=None
        def current_identity_bundle(self, purpose, audience):
            assert (purpose, audience)==(api.PURPOSE,api.AUDIENCE)
            self.calls+=1; boundary[3].append('identity_metadata')
            return self.replacement if self.calls>1 and self.replacement else self.value
    owner=Owner()
    client=boundary[0]
    client.app.state.company_context_owner=owner
    return client, owner, records, bundle


def test_context_runtime_needs_no_disclosure_capability(context_fixture, boundary):
    client, owner, *_ = context_fixture
    client.app.state.company_context_owner = owner
    del client.app.state.company_disclosure_reader
    response = context_get(context_fixture)
    assert response.status_code == 200, response.text
    assert boundary[4].calls == 0 and 'private_store' not in boundary[3]
    private_headers(response)


def context_get(fixture, query='?symbol=AAA'):
    return fixture[0].get('/api/company-intelligence/private/company-context'+query,
                           headers={'Authorization':'Bearer synthetic-token'})


def test_context_resolves_actual_owner_values_and_same_issuer_receipt_for_share_classes(context_fixture,boundary):
    from hashlib import sha256
    import json
    one=context_get(context_fixture); two=context_get(context_fixture,'?symbol=AAB')
    assert one.status_code==two.status_code==200
    a,b=one.json(),two.json(); assert a['security_id']!=b['security_id']
    assert a['issuer_binding']==b['issuer_binding'] and a['identity_receipt']==b['identity_receipt']
    raw=json.dumps(a['identity_receipt'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    ref=a['issuer_binding']['identity_snapshot_reference']
    assert ref['sha256']==sha256(raw).hexdigest() and ref['byte_length']==len(raw)<=16384
    assert a['query']=={'namespace':'store','symbol':'AAA'} and a['identity_mode']=='current'
    assert 'private_store' not in boundary[3]
    private_headers(one)


@pytest.mark.parametrize('query',['?symbol=^NDX','?symbol=aaa','?symbol=AAA&symbol=AAB',
    '?symbol=AAA&vendor=yahoo','?symbol=AAA&on=2025-01-01','?issuer_id=ISS:US-XNAS-AAA',''])
def test_context_query_cannot_supply_identity_namespace_or_time(context_fixture,boundary,query):
    result=context_get(context_fixture,query); assert result.status_code==400
    assert context_fixture[1].calls==0 and 'private_store' not in boundary[3];private_headers(result)


@pytest.mark.parametrize('symbol',['UNKNOWN','AAA.B','AAA-B'])
def test_context_does_not_invent_aliases(context_fixture,symbol):
    result=context_get(context_fixture,'?symbol='+symbol)
    assert result.status_code==503 and result.json()['code']=='PRIVATE_SOURCE_UNAVAILABLE'


@pytest.mark.parametrize('mutation',['duplicate_security','duplicate_issuer','ambiguous_alias','superseded',
    'no_issuer_evidence','wrong_cik','wrong_snapshot','listing_mismatch','wrong_market'])
def test_context_refuses_unqualified_reference_composition(context_fixture,mutation):
    import copy
    client,owner,original,bundle=context_fixture; data=copy.deepcopy(original)
    if mutation=='duplicate_security': data['security_master'].append(data['security_master'][0].copy())
    elif mutation=='duplicate_issuer': data['issuer_master'].append(data['issuer_master'][0].copy())
    elif mutation=='ambiguous_alias': data['vendor_aliases'].append(dict(data['vendor_aliases'][0],security_id='SEC:US-XNAS-AAB'))
    elif mutation=='superseded': data['security_master'][0]['superseded_by']='SEC:US-XNAS-AAB'
    elif mutation=='no_issuer_evidence': data['security_master'][0]['issuer_state']='NO_ISSUER_EVIDENCE'
    elif mutation=='wrong_cik': data['issuer_master'][0]['cik']='0000000002'
    elif mutation=='wrong_snapshot':
        from datetime import date
        data['issuer_master'][0]['evidence_snapshot']=date(2025,1,1)
    elif mutation=='listing_mismatch': data['security_master'][0]['listing_key']='US-XNAS-AAB'
    elif mutation=='wrong_market':
        data['security_master'][0]['security_id']='SEC:HK-XHKG-0001'
        data['security_master'][0]['listing_key']='HK-XHKG-0001'
        data['vendor_aliases'][0]['security_id']='SEC:HK-XHKG-0001'
    owner.value=bundle(data)
    result=context_get(context_fixture); assert result.status_code==503;private_headers(result)


def test_context_rechecks_bundle_generation_before_response(context_fixture):
    owner=context_fixture[1];owner.replacement=replace(owner.value,source_commit='b'*40)
    result=context_get(context_fixture);assert result.status_code==503 and owner.calls==2


def test_context_auth_and_feature_precede_reference_metadata(context_fixture,boundary):
    client,owner,*_=context_fixture
    result=client.get('/api/company-intelligence/private/company-context?symbol=AAA')
    assert result.status_code==401 and owner.calls==0
    boundary[2]['features']=[]
    result=context_get(context_fixture);assert result.status_code==403 and owner.calls==0
    assert 'private_store' not in boundary[3]


@pytest.mark.parametrize('bad',['corrupt','oversize','unqualified_generation'])
def test_context_invalid_bundle_is_sanitized(context_fixture,bad):
    from engine.company_intelligence import current_company_context as context
    owner=context_fixture[1]
    if bad=='corrupt':owner.value=replace(owner.value,issuer_master=b'not parquet')
    elif bad=='oversize':owner.value=replace(owner.value,issuer_master=b'x'*(context.MAX_REFERENCE_BYTES+1))
    else:owner.value=replace(owner.value,source_commit='not-a-source-commit')
    result=context_get(context_fixture);assert result.status_code==503
    assert 'not parquet' not in result.text and 'not-a-source-commit' not in result.text
    private_headers(result)


def test_context_absent_runtime_is_not_a_public_fallback(boundary):
    result=context_get((boundary[0],));assert result.status_code==503
    assert result.json()['code']=='SOURCE_RUNTIME_UNAVAILABLE' and 'private_store' not in boundary[3]

@pytest.mark.parametrize('gap',['issuer_kind','zero_cik','future_snapshot','invalid_snapshot'])
def test_context_review_gap_rejects_noncanonical_or_future_evidence(context_fixture,gap):
    import copy
    from datetime import date
    owner=context_fixture[1];data=copy.deepcopy(context_fixture[2])
    if gap=='issuer_kind':
        for row in data['security_master']:row['issuer_id']='SEC:US-XNAS-AAA'
        data['issuer_master'][0]['issuer_id']='SEC:US-XNAS-AAA'
    elif gap=='zero_cik':
        for row in data['security_master']:row['issuer_cik']='0000000000'
        data['issuer_master'][0]['cik']='0000000000'
    else:
        value=date(2099,1,1) if gap=='future_snapshot' else 'not-a-date'
        for row in data['security_master']:row['issuer_evidence_snapshot']=value
        data['issuer_master'][0]['evidence_snapshot']=value
    owner.value=context_fixture[3](data)
    assert context_get(context_fixture).status_code==503


def test_context_review_gap_midnight_expiry_refuses(context_fixture,monkeypatch):
    import copy
    from datetime import date,datetime,timezone
    from engine.company_intelligence import current_company_context as context
    data=copy.deepcopy(context_fixture[2]);data['vendor_aliases'][0]['valid_to']=date(2026,10,12)
    context_fixture[1].value=context_fixture[3](data)
    class Clock:
        calls=0
        @classmethod
        def now(cls,tz):
            cls.calls+=1
            return datetime(2026,10,11,23,59,59,tzinfo=timezone.utc) if cls.calls==1 else datetime(2026,10,12,tzinfo=timezone.utc)
    monkeypatch.setattr(context,'datetime',Clock)
    assert context_get(context_fixture).status_code==503
