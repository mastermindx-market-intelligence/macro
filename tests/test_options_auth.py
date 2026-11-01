"""Actual Macro readers with inert HTTP/store; no live auth or source grant."""
import base64
from dataclasses import replace
import json
import sys
from types import SimpleNamespace
import urllib.error

import pytest

from app import billing, options_auth as M, paywall
from tests import test_options_use as U

UID = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
SID = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'
URL = 'https://auth-fixture.invalid'
ISS = URL + '/auth/v1'


def token(**changes):
    claims = dict(sub=UID, iss=ISS, session_id=SID, role='authenticated',
                  exp=2000, is_anonymous=False)
    claims.update(changes)
    return raw_token(json.dumps(claims))


def raw_token(payload):
    return 'e30.' + base64.urlsafe_b64encode(payload.encode()).decode().rstrip('=') + '.c2ln'


def request(**changes):
    fields = dict(request_id='synthetic', principal_id=UID, principal_issuer=ISS,
                  auth_epoch=SID, owner='options_structure.matrix', schema='options_structure.matrix/v1',
                  root='SPY', sha256='a'*64, byte_length=1, session='2026-10-12',
                  vendor='thetadata', underlying_id='SEC:US-ARCX-SYNTH', selection_sha256='b'*64,
                  action='display')
    fields.update(changes)
    return M.OptionUseRequest(**fields)


@pytest.fixture
def env(monkeypatch):
    state = SimpleNamespace(auth_calls=0, store_calls=0, store_ids=[], operator=False,
                            row=dict(tier='pro', features=['terminal_live_options'], status='active'),
                            user=dict(id=UID, email='fixture@example.invalid', is_anonymous=False),
                            auth_error=None, store_error=None, now=1000)
    main = SimpleNamespace(SUPABASE_URL=URL, SUPABASE_ANON_KEY='synthetic',
                           _brain_module=lambda: SimpleNamespace(_unlimited_allowed=lambda email: state.operator))
    monkeypatch.setitem(sys.modules, 'app.main', main)
    monkeypatch.setattr(M.time, 'time', lambda: state.now)
    monkeypatch.setattr(billing, 'SUPABASE_SERVICE_ROLE_KEY', 'synthetic')
    def http(req, timeout):
        state.auth_calls += 1
        assert req.full_url == URL + '/auth/v1/user' and timeout == 4
        if state.auth_error:
            raise state.auth_error
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return json.dumps(state.user).encode()
        return Response()
    def pg(method, path, **kwargs):
        state.store_calls += 1
        assert method == 'GET' and path.startswith('user_entitlements?user_id=eq.')
        state.store_ids.append(path.split('eq.')[1].split('&')[0])
        if state.store_error:
            raise state.store_error
        return [] if state.row is None else [state.row]
    monkeypatch.setattr(paywall.urllib.request, 'urlopen', http)
    monkeypatch.setattr(billing, '_pg', pg)
    def forbidden(*args, **kwargs): raise AssertionError('cache/grace used')
    monkeypatch.setattr(paywall, '_resolve_identity', forbidden)
    monkeypatch.setattr(paywall, '_entitled', forbidden)
    state.main = main
    return state


def test_real_auth_and_billing_readers_bind_principal(env):
    p = M.resolve_options_principal(token())
    assert (p.principal_id, p.principal_issuer, p.auth_epoch, p.expires_at) == (UID, ISS, SID, 2000)
    assert 'e30.' not in repr(p)
    assert M.fresh_options_entitlement(request(), access_token=token()) is True
    assert (env.auth_calls, env.store_calls, env.store_ids) == (2, 1, [UID])


@pytest.mark.parametrize('value', [None, b'token', '', ' '+token(), token()+'\n', 'x.y', 'x.y.z.q', 'x'*16385])
def test_invalid_token_does_not_contact_auth(env, value):
    with pytest.raises(M.OptionUseRefused, match='authentication_unavailable'):
        M.resolve_options_principal(value)
    assert env.auth_calls == env.store_calls == 0


@pytest.mark.parametrize('changes', [dict(sub='bad'), dict(sub=SID), dict(iss=URL),
    dict(iss='https://foreign.invalid/auth/v1'), dict(session_id=None), dict(session_id=''),
    dict(session_id='not-uuid'), dict(role='service_role'), dict(role='anon'),
    dict(exp=1000), dict(exp=999), dict(exp=True), dict(exp='2000'), dict(exp=2000.5),
    dict(is_anonymous=True), dict(is_anonymous='false')])
def test_accepted_auth_token_still_needs_exact_claim_binding(env, changes):
    assert M.fresh_options_entitlement(request(), access_token=token(**changes)) is False
    assert env.auth_calls == 1 and env.store_calls == 0


@pytest.mark.parametrize('payload', ['[]', 'null', '{', '{"sub":"a","sub":"b"}',
                                  '{"x":NaN}', '{"x":Infinity}', '{"x":'+('['*1100)+(']'*1100)+'}'])
def test_ambiguous_or_invalid_claims_refuse(env, payload):
    assert not M.fresh_options_entitlement(request(), access_token=raw_token(payload))
    assert env.store_calls == 0


@pytest.mark.parametrize('field,value', [('principal_id', SID), ('principal_issuer', URL),
    ('auth_epoch', UID), ('principal_id', None), ('auth_epoch', None)])
def test_foreign_subject_issuer_session_never_reads_entitlement(env, field, value):
    assert not M.fresh_options_entitlement(request(**{field:value}), access_token=token())
    assert env.auth_calls == 1 and env.store_calls == 0


@pytest.mark.parametrize('bad_url', ['', None, 'http://fixture.invalid', URL+'/path', URL+'?q=x',
    URL+'#fragment', 'https://x@fixture.invalid', ' '+URL, URL+'\n'])
def test_bad_server_issuer_refuses_before_auth(env, bad_url):
    env.main.SUPABASE_URL = bad_url
    assert not M.fresh_options_entitlement(request(), access_token=token())
    assert env.auth_calls == env.store_calls == 0


@pytest.mark.parametrize('status', [400,401,403,429,500])
def test_auth_failure_after_prior_success_never_borrows_cache(env, status):
    assert M.fresh_options_entitlement(request(), access_token=token())
    env.auth_error = urllib.error.HTTPError(URL, status, 'synthetic', {}, None)
    assert not M.fresh_options_entitlement(request(), access_token=token())
    assert (env.auth_calls, env.store_calls) == (2,1)


def test_busy_original_semaphore_refuses_without_network(env, monkeypatch):
    monkeypatch.setattr(paywall, '_AUTH_UPSTREAM_SEM', SimpleNamespace(acquire=lambda **kw: False))
    assert not M.fresh_options_entitlement(request(), access_token=token())
    assert env.auth_calls == env.store_calls == 0


@pytest.mark.parametrize('user', [{}, {'id':'bad'}, {'id':SID}, {'id':UID, 'is_anonymous':True},
                               {'id':UID,'is_anonymous':'false'}])
def test_bad_or_different_returned_user(env,user):
    env.user=user
    assert not M.fresh_options_entitlement(request(), access_token=token())
    assert env.store_calls==0


@pytest.mark.parametrize('tier,features,expected', [
    ('free',[],False), ('pro',[],False), ('essential',['terminal_live_options'],True),
    ('free',['terminal_live_options'],True), (' unlimited ',[],True),
    ('pro','terminal_live_options',False), ('pro',{'terminal_live_options':True},False),
    ('pro',['site_full'],False), (None,[],False), ('pro',None,False)])
def test_exact_existing_product_predicate(env,tier,features,expected):
    env.row=dict(tier=tier,features=features,status='none')
    assert M.fresh_options_entitlement(request(),access_token=token()) is expected


def test_operator_uses_same_verified_email_overlay(env):
    env.row=None
    env.operator=True
    assert M.fresh_options_entitlement(request(),access_token=token())
    env.auth_error=urllib.error.HTTPError(URL,401,'synthetic',{},None)
    assert not M.fresh_options_entitlement(request(),access_token=token())


def test_downgrade_and_outage_never_reuse_success(env):
    assert M.fresh_options_entitlement(request(),access_token=token())
    env.row=None
    assert not M.fresh_options_entitlement(request(),access_token=token())
    env.store_error=RuntimeError('synthetic secret that must not escape')
    assert not M.fresh_options_entitlement(request(),access_token=token())
    assert env.auth_calls==env.store_calls==3


def test_expiry_during_billing_refuses(env,monkeypatch):
    real=billing.read_entitlement
    def read(uid):
        value=real(uid)
        env.now=2000
        return value
    monkeypatch.setattr(billing,'read_entitlement',read)
    assert not M.fresh_options_entitlement(request(),access_token=token())


def test_exception_text_is_not_returned(env):
    env.auth_error=RuntimeError('synthetic-secret '+token())
    with pytest.raises(M.OptionUseRefused) as caught:
        M.resolve_options_principal(token())
    assert str(caught.value)=='authentication_unavailable'
    assert not M.fresh_options_entitlement(request(),access_token=token())


@pytest.mark.parametrize('action',['display','export'])
def test_actual_identity_selection_and_rights_composition(env,action):
    s=U.setup.__wrapped__()
    kw=dict(s['kw'])
    for key in ('principal_id','principal_issuer','auth_epoch','fresh_entitlement'):
        kw.pop(key)
    kw['action']=action
    result=M.resolve_authenticated_option_selection(s['ref'],s['matrix'],s['selected'],
                                                   access_token=token(),**kw)
    assert result.request.principal_id==UID and result.request.auth_epoch==SID
    assert result.request.action==action and result.selection.primary.strike=='500'
    assert env.auth_calls==2 and env.store_calls==1
    assert [x[0] for x in s['calls']]==['rights']


@pytest.mark.parametrize('failure',['rights_absent','rights_denied','selection_bad','second_auth_denied'])
def test_composition_never_releases_on_missing_gates(env,monkeypatch,failure):
    s=U.setup.__wrapped__()
    kw=dict(s['kw'])
    for key in ('principal_id','principal_issuer','auth_epoch','fresh_entitlement'):
        kw.pop(key)
    if failure=='rights_absent': kw['source_use_decision']=None
    if failure=='rights_denied': kw['source_use_decision']=lambda req: U.allow(req,status='denied')
    if failure=='selection_bad': s['selected']=b'{}'
    if failure=='second_auth_denied':
        real=paywall._fetch_supabase_user
        def fetch(tok):
            if env.auth_calls: env.auth_error=urllib.error.HTTPError(URL,401,'synthetic',{},None)
            return real(tok)
        monkeypatch.setattr(paywall,'_fetch_supabase_user',fetch)
    with pytest.raises(M.OptionUseRefused):
        M.resolve_authenticated_option_selection(s['ref'],s['matrix'],s['selected'],access_token=token(),**kw)
    assert not s['calls']
    if failure=='rights_absent': assert env.auth_calls==env.store_calls==0
    if failure=='second_auth_denied': assert env.auth_calls==2 and env.store_calls==0
