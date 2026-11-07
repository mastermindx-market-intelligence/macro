"""Pure/fake transport contract only; no SQL, credentials or native capture."""
import io
import json
import sys
from dataclasses import replace
from types import SimpleNamespace

import pytest

from app import investigation_native_capture as N

ORIGIN = 'https://project-fixture.invalid'
ACTOR = '10000000-0000-4000-8000-000000000001'
OP = '20000000-0000-4000-8000-000000000002'
EPOCH = '30000000-0000-4000-8000-000000000003'
GEN = '40000000-0000-4000-8000-000000000004'
BINDING = dict(actor=ACTOR, operation_id=OP, issuer=ORIGIN+'/auth/v1', auth_epoch=EPOCH,
               request_sha256='a'*64, source_binding_sha256='b'*64)


REQUEST={'principal':ACTOR,'action':'create','target':GEN,'expected_revision':0,'manifest':{},'layout_capture':None}

def binding():
    return N.CaptureBinding(**BINDING)


class Body(io.BytesIO):
    status = 200


def authority(reply=None, fail=None):
    calls=[]
    def opener(request, timeout):
        calls.append((request, timeout))
        if fail: raise fail
        return Body(json.dumps(reply).encode())
    return N.NativeCaptureAuthority(ORIGIN, 'FIXTURE-SERVER-SECRET', opener), calls


def response(status='claimed', **changes):
    return dict(schema='investigation.native_capture.v1',status=status,generation=GEN,binding=BINDING,**changes)


def test_claim_is_one_fixed_server_rpc_and_never_exposes_server_key():
    owner,calls=authority(response()); observed=owner.claim(binding(), REQUEST)
    assert observed.status=='claimed' and observed.generation==GEN
    request,timeout=calls[0]
    assert request.full_url==ORIGIN+'/rest/v1/rpc/claim_investigation_native_capture_v1'
    assert request.get_header('Authorization')=='Bearer FIXTURE-SERVER-SECRET'
    assert json.loads(request.data)=={'p_binding':BINDING,'p_request':REQUEST}
    assert timeout==6 and len(calls)==1
    assert 'SECRET' not in repr(owner)+repr(observed)


def test_existing_is_an_observation_never_an_execution_or_settlement_grant():
    owner,calls=authority(response('existing')); observed=owner.claim(binding(), REQUEST)
    assert observed.status=='existing' and not hasattr(observed,'execute')
    assert not hasattr(observed,'completed') and len(calls)==1


def test_lost_claim_and_completion_never_retry_or_fallback():
    owner,calls=authority(fail=TimeoutError('SECRET'))
    with pytest.raises(N.NativeCaptureUnavailable, match='native_rpc_unavailable') as lost: owner.claim(binding(), REQUEST)
    assert 'SECRET' not in str(lost.value)
    assert len(calls)==1
    claim=N.ClaimObservation('claimed',GEN,binding())
    with pytest.raises(N.NativeCaptureUnavailable, match='native_rpc_unavailable'): owner.record_retained(claim)
    assert len(calls)==2


@pytest.mark.parametrize('key,value',[('actor',OP),('operation_id',ACTOR),('auth_epoch',OP),('issuer','https://other.invalid/auth/v1'),('request_sha256','c'*64),('source_binding_sha256','c'*64)])
def test_wrong_binding_echo_refuses(key,value):
    reply=response();reply['binding']={**BINDING,key:value}
    owner,_=authority(reply)
    with pytest.raises(N.NativeCaptureUnavailable): owner.claim(binding(), REQUEST)


def test_partial_unknown_extra_or_unverified_reply_never_claims():
    for raw in [None,{},response('unknown'),{**response(),'ready':True},{**response(),'generation':True}]:
        owner,_=authority(raw)
        with pytest.raises(N.NativeCaptureUnavailable): owner.claim(binding(), REQUEST)


def test_only_original_claim_generation_can_record_retained():
    claim=N.ClaimObservation('claimed',GEN,binding())
    raw=response('recorded',native_phase='retained')
    owner,calls=authority(raw)
    result=owner.record_retained(claim)
    assert result.native_phase=='retained' and result.generation==GEN
    assert calls[0][0].full_url.endswith('/complete_investigation_native_capture_v1')
    payload=json.loads(calls[0][0].data)
    assert payload=={'p_binding':BINDING,'p_generation':GEN,'p_native_phase':'retained'}
    for changed in [{**raw,'generation':OP},{**raw,'native_phase':'unknown'},response('recorded')]:
        other,_=authority(changed)
        with pytest.raises(N.NativeCaptureUnavailable):other.record_retained(claim)
    with pytest.raises(N.NativeCaptureUnavailable):owner.record_retained(replace(claim,status='existing'))


@pytest.mark.parametrize('issuer',['http://project-fixture.invalid/auth/v1','https://user:secret@project-fixture.invalid/auth/v1','https://project-fixture.invalid/auth/v1?x=1',ORIGIN+'/auth/v1\n'])
def test_invalid_or_foreign_project_refuses_before_transport(issuer):
    owner,calls=authority(response())
    with pytest.raises((ValueError,N.NativeCaptureUnavailable)):
        owner.claim(N.CaptureBinding(**{**BINDING,'issuer':issuer}))
    assert calls==[]


def test_runtime_factory_uses_only_incumbent_same_project_server_reference(monkeypatch):
    from app import options_scenarios as S
    monkeypatch.setitem(sys.modules,'app.main',SimpleNamespace(SUPABASE_URL=ORIGIN,SUPABASE_SERVICE_ROLE_KEY='FIXTURE-SERVER-SECRET',SUPABASE_ANON_KEY='FIXTURE-PUBLIC'))
    monkeypatch.setattr(S,'_open_rpc',lambda *_:pytest.fail('no transport during construction'))
    owner=N.from_server_runtime()
    assert 'SECRET' not in repr(owner)
    monkeypatch.setitem(sys.modules,'app.main',SimpleNamespace(SUPABASE_URL=ORIGIN,SUPABASE_SERVICE_ROLE_KEY='',SUPABASE_ANON_KEY='FIXTURE-PUBLIC'))
    with pytest.raises(N.NativeCaptureUnavailable):N.from_server_runtime()
