"""Controlled negative HTTP boundary; no fleet, auth, SQL or native drain proof."""
import asyncio
from contextvars import copy_context
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

import pytest
from fastapi import FastAPI

from app import options_scenario_http_admission as H
from app import investigation_native_capture as N
from tests.test_investigation_native_capture import BINDING, REQUEST, GEN, binding, authority, response


def installed(monkeypatch, *, source='1', capture='1'):
    monkeypatch.setenv('OPTIONS_SCENARIO_SOURCE_ENABLED', source)
    monkeypatch.setenv('OPTIONS_SCENARIO_CAPTURE_ENABLED', capture)
    app = FastAPI()
    guard = H.install_http_admission(app)
    owner, calls = authority(response())
    backend = SimpleNamespace(native_capture_authority=owner)
    app.state.options_scenario_source_bindings = backend
    principal = SimpleNamespace(principal_id=BINDING['actor'], principal_issuer=BINDING['issuer'],
                                auth_epoch=BINDING['auth_epoch'])
    return SimpleNamespace(app=app, guard=guard, backend=backend, owner=owner, calls=calls,
                           principal=principal, request=SimpleNamespace(app=app))


def bind(h, request=None):
    H.bind_capture_request(h.principal, BINDING['operation_id'], request or REQUEST)


def enter_claim(h, b=None, request=None):
    H.require_claim_admission(h.owner, b or binding(), request or REQUEST)


@pytest.mark.parametrize('flag', ['OPTIONS_SCENARIO_SOURCE_ENABLED', 'OPTIONS_SCENARIO_CAPTURE_ENABLED'])
@pytest.mark.parametrize('initial', ['0', '', 'true'])
def test_boot_ceiling_cannot_be_raised_or_reinstalled(monkeypatch, flag, initial):
    h = installed(monkeypatch, source=initial if 'SOURCE' in flag else '1',
                  capture=initial if 'CAPTURE' in flag else '1')
    monkeypatch.setenv(flag, '1')
    assert H.install_http_admission(h.app) is h.guard
    with pytest.raises(H.AdmissionClosed):
        with H.request_lifetime(h.request, h.backend):
            bind(h)
            enter_claim(h)
    assert h.calls == []


@pytest.mark.parametrize('flag', ['OPTIONS_SCENARIO_SOURCE_ENABLED', 'OPTIONS_SCENARIO_CAPTURE_ENABLED'])
def test_observed_closed_latches_after_environment_reopens(monkeypatch, flag):
    h = installed(monkeypatch)
    with H.request_lifetime(h.request, h.backend):
        bind(h)
        monkeypatch.delenv(flag)
        with pytest.raises(H.AdmissionClosed): enter_claim(h)
        monkeypatch.setenv(flag, '1')
        with pytest.raises(H.AdmissionClosed): enter_claim(h)
    assert H.install_http_admission(h.app) is h.guard and not h.calls


def test_missing_installer_and_foreign_app_guard_refuse(monkeypatch):
    h = installed(monkeypatch)
    other = FastAPI(); other.state.options_scenario_source_bindings = h.backend
    with pytest.raises(H.AdmissionClosed):
        with H.request_lifetime(SimpleNamespace(app=other), h.backend): pass
    other.state.options_scenario_http_admission = h.guard
    with pytest.raises(H.AdmissionClosed): H.install_http_admission(other)
    with pytest.raises(H.AdmissionClosed):
        with H.request_lifetime(SimpleNamespace(app=other), h.backend): pass


def test_no_request_or_unbound_request_has_no_claim_entry(monkeypatch):
    h = installed(monkeypatch)
    with pytest.raises(H.AdmissionClosed): bind(h)
    with pytest.raises(H.AdmissionClosed): enter_claim(h)
    with H.request_lifetime(h.request, h.backend):
        with pytest.raises(H.AdmissionClosed): enter_claim(h)
    assert not h.calls


def test_binding_is_single_original_request_and_immutable_snapshot(monkeypatch):
    h = installed(monkeypatch); original = deepcopy(REQUEST)
    with H.request_lifetime(h.request, h.backend):
        bind(h, original)
        with pytest.raises(H.AdmissionClosed): bind(h, original)
        original['manifest']['injected'] = True
        with pytest.raises(H.AdmissionClosed): enter_claim(h, request=original)
        enter_claim(h, request=REQUEST)
        with pytest.raises(H.AdmissionClosed): enter_claim(h)
    assert not h.calls  # Local entry permission is never a SQL claim observation.


@pytest.mark.parametrize('field,value', [('actor', GEN), ('operation_id', GEN),
    ('issuer', 'https://foreign.invalid/auth/v1'), ('auth_epoch', GEN)])
def test_foreign_actor_operation_issuer_or_session_refuses(monkeypatch, field, value):
    h = installed(monkeypatch)
    with H.request_lifetime(h.request, h.backend):
        bind(h)
        with pytest.raises(H.AdmissionClosed): enter_claim(h, replace(binding(), **{field:value}))
        enter_claim(h)
    assert not h.calls


def test_backend_or_authority_replacement_does_not_inherit_scope(monkeypatch):
    h = installed(monkeypatch)
    with H.request_lifetime(h.request, h.backend):
        bind(h)
        other, _ = authority(response())
        with pytest.raises(H.AdmissionClosed): H.require_claim_admission(other, binding(), REQUEST)
        h.app.state.options_scenario_source_bindings = SimpleNamespace(native_capture_authority=h.owner)
        with pytest.raises(H.AdmissionClosed): enter_claim(h)
    assert not h.calls


def test_reentrant_and_cross_request_context_cannot_borrow_scope(monkeypatch):
    h = installed(monkeypatch); other = installed(monkeypatch)
    with H.request_lifetime(h.request, h.backend):
        bind(h)
        for target in (h, other):
            with pytest.raises(H.AdmissionClosed):
                with H.request_lifetime(target.request, target.backend): pass
        copied = copy_context()
    with H.request_lifetime(other.request, other.backend):
        bind(other)
        with pytest.raises(H.AdmissionClosed): copied.run(enter_claim, h)
        enter_claim(other)
    with pytest.raises(H.AdmissionClosed): copied.run(bind, h)
    with pytest.raises(H.AdmissionClosed):
        copied.run(lambda: H.request_lifetime(h.request, h.backend).__enter__())


def test_real_async_child_copied_context_is_revoked_after_response_finally(monkeypatch):
    h = installed(monkeypatch)
    async def exercise():
        proceed = asyncio.Event()
        async def child():
            await proceed.wait()
            with pytest.raises(H.AdmissionClosed): enter_claim(h)
        with H.request_lifetime(h.request, h.backend):
            bind(h)
            task = asyncio.create_task(child())
        proceed.set()
        await task
    asyncio.run(exercise())
    assert not h.calls


def test_concurrent_request_lifetimes_are_isolated(monkeypatch):
    h = installed(monkeypatch); other = installed(monkeypatch)
    other.principal = SimpleNamespace(principal_id=GEN, principal_issuer=BINDING['issuer'], auth_epoch=GEN)
    async def exercise():
        a, b = asyncio.Event(), asyncio.Event()
        async def first():
            with H.request_lifetime(h.request, h.backend):
                bind(h); a.set(); await b.wait()
                enter_claim(h)
        async def second():
            await a.wait()
            request = {**REQUEST, 'principal':GEN}
            with H.request_lifetime(other.request, other.backend):
                H.bind_capture_request(other.principal, GEN, request)
                with pytest.raises(H.AdmissionClosed): enter_claim(h)
                H.require_claim_admission(other.owner, replace(binding(), actor=GEN,
                    auth_epoch=GEN, operation_id=GEN), request)
                b.set()
        await asyncio.gather(first(), second())
    asyncio.run(exercise())


def test_exception_finally_revokes_copy_and_new_request_can_enter(monkeypatch):
    h = installed(monkeypatch)
    with pytest.raises(RuntimeError):
        with H.request_lifetime(h.request, h.backend):
            bind(h); copied = copy_context()
            raise RuntimeError('controlled handler exception')
    with pytest.raises(H.AdmissionClosed): copied.run(enter_claim, h)
    with H.request_lifetime(h.request, h.backend): bind(h); enter_claim(h)


def test_original_factual_completion_survives_ended_closed_scope(monkeypatch):
    h = installed(monkeypatch)
    with H.request_lifetime(h.request, h.backend):
        bind(h); enter_claim(h)
        claim = h.owner.claim(binding(), REQUEST)
    monkeypatch.setenv('OPTIONS_SCENARIO_SOURCE_ENABLED', '0')
    completion_owner, calls = authority(response('recorded', native_phase='retained'))
    result = completion_owner.record_retained(claim)
    assert result.generation == GEN and result.native_phase == 'retained' and len(calls) == 1
    # The incumbent non-HTTP native owner remains usable without an HTTP actor.
    assert h.owner.claim(binding(), REQUEST).status == 'claimed'


# Real incumbent installer -> mounted route -> preclaim. External boundaries are
# existing controlled transport doubles, not runtime credentials or SQL rights.
from tests.test_scenario_initial_capture import runtime_setup, canonical_intent, setup
from tests.test_options_scenarios import World, token, INV_B, OP
from app import options_scenarios as S


def capture_payload(h):
    return canonical_intent(dict(mode='capture', investigation_id=INV_B, revision=1,
        expected_revision=0, operation_id=OP, grant_id=None, capture=h.capture()))


def test_installed_mounted_route_closure_precedes_fresh_auth_and_all_io(monkeypatch, tmp_path):
    h, client, _ = runtime_setup(monkeypatch, tmp_path, capture_enabled=True)
    monkeypatch.setenv('OPTIONS_SCENARIO_SOURCE_ENABLED', '0')
    before = h.state.auth_calls
    assert h.post(client, capture_payload(h), token_value=token()).json()['reason'] == 'source_binding_unavailable'
    monkeypatch.setenv('OPTIONS_SCENARIO_SOURCE_ENABLED', '1')
    assert h.post(client, capture_payload(h), token_value=token()).json()['reason'] == 'source_binding_unavailable'
    assert h.state.auth_calls == before and not h.trace and not h.s3.log


def test_real_installer_boot_closed_is_not_reopened(monkeypatch):
    from app import options_scenario_bindings as B
    h = World(); h.patch(monkeypatch)
    monkeypatch.setenv('OPTIONS_SCENARIO_SOURCE_ENABLED', '0')
    client = h.client(bind=False)
    B.install_scenario_sources(h.app)
    monkeypatch.setenv('OPTIONS_SCENARIO_SOURCE_ENABLED', '1')
    monkeypatch.setattr(B.r2_store, 'build_store', lambda **kw: pytest.fail('closed boot reached store'))
    B.install_scenario_sources(h.app)
    assert h.post(client, h.resolve_payload(), token_value=token()).json()['reason'] == 'source_binding_unavailable'
    assert not h.trace and h.state.auth_calls == 0


@pytest.mark.parametrize('guard_present', [True, False])
def test_mounted_request_close_immediately_before_claim_is_causal(monkeypatch, tmp_path, guard_present):
    h = World(); client, payload, _ = setup(h, monkeypatch, tmp_path)
    original = N.binding_for
    def close(*args, **kwargs):
        result = original(*args, **kwargs)
        monkeypatch.setenv('OPTIONS_SCENARIO_CAPTURE_ENABLED', '0')
        return result
    monkeypatch.setattr(N, 'binding_for', close)
    if not guard_present:
        # Controlled counterfactual: the incumbent flow otherwise dispatches the
        # native claim after closure. This grants no runtime bypass or permission.
        monkeypatch.setattr(H, 'require_claim_admission', lambda *args: None)
    observed = h.post(client, payload, token_value=token()).json()
    assert h.state.auth_calls > 0
    if guard_present:
        assert observed['status'] == 'unavailable'
        assert not h.native_rpc_calls and not h.s3.log
    else:
        assert observed.get('mode') == 'capture', observed
        assert [kind for kind, _ in h.native_rpc_calls] == ['claim', 'complete']
        assert h.s3.log


def test_mounted_close_after_claim_never_aborts_original_completion(monkeypatch, tmp_path):
    h = World(); client, payload, _ = setup(h, monkeypatch, tmp_path)
    original = N.NativeCaptureAuthority.claim
    def close(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        monkeypatch.setenv('OPTIONS_SCENARIO_SOURCE_ENABLED', '0')
        return result
    monkeypatch.setattr(N.NativeCaptureAuthority, 'claim', close)
    observed = h.post(client, payload, token_value=token()).json()
    assert observed.get('mode') == 'capture', observed
    assert [kind for kind, _ in h.native_rpc_calls] == ['claim', 'complete']
    assert h.native_phases[OP]['state'] == 'retained'
    before = len(h.s3.log)
    assert h.post(client, payload, token_value=token()).json()['reason'] == 'source_binding_unavailable'
    assert len(h.s3.log) == before and len(h.native_rpc_calls) == 2
