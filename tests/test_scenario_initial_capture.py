"""Controlled ingress and original acquisition; no live rights/store binding."""
from dataclasses import replace
from pathlib import Path
from copy import deepcopy
import hashlib
import json

from app import hub, options_scenarios as S
from tests.test_options_scenarios import World, token, INV_B, OP, FakeRpcResponse
from tests.test_options_hub_retention import FakeS3, controlled_decision


def setup(h, monkeypatch, tmp_path):
    h.patch(monkeypatch)
    monkeypatch.setattr(S, '_open_rpc', lambda *args, **kwargs: FakeRpcResponse({'status':'not_found'}))
    h.s3 = FakeS3()
    for kind, raw in [('gex',h.gex_bytes),('moves',h.moves_bytes)]:
        path=tmp_path/kind/'SPY.json';path.parent.mkdir();path.write_bytes(raw)
    client=h.client()
    base=h.app.state.options_scenario_source_bindings
    calls=[]
    def save(binding):
        calls.append(deepcopy(binding))
        return {**h.source_use_decision(binding),'status':'allowed'}
    h.app.state.options_scenario_source_bindings=replace(base, producer_out_dir=tmp_path,
        source_save_decision=save,retention_decision=controlled_decision())
    payload={'mode':'capture','investigation_id':INV_B,'revision':1,'expected_revision':0,
        'operation_id':OP,'grant_id':None,'capture':h.capture()}
    return client,payload,calls


def test_capture_default_refuses_before_auth_files_or_store(monkeypatch):
    h=World();h.patch(monkeypatch);client=h.client()
    payload={'mode':'capture','investigation_id':INV_B,'revision':1,'expected_revision':0,
        'operation_id':OP,'grant_id':None,'capture':h.capture()}
    response=h.post(client,payload,token_value=token())
    assert response.status_code==200 and response.json()['reason']=='source_binding_unavailable'
    assert not h.trace and h.state.auth_calls==0


def test_initial_capture_retains_exact_bytes_before_returning_for_native_math(monkeypatch,tmp_path):
    h=World();client,payload,calls=setup(h,monkeypatch,tmp_path)
    response=h.post(client,payload,token_value=token())
    assert response.status_code==200,response.text
    assert response.json()['mode']=='capture'
    assert calls[0]['action']=='save_scenario_sources' and calls[0]['operation_id']==OP
    assert h.s3.objects[h.gex_ref.key]==h.gex_bytes
    assert h.s3.objects[h.moves_ref.key]==h.moves_bytes
    assert response.headers['cache-control']=='private, no-store'
    puts=sum(x[0]=='put' for x in h.s3.log)
    # Recovery is QUALIFY (read only); it never replays retention, even same op.
    response=h.post(client,{**payload,'mode':'qualify'},token_value=token())
    assert response.status_code==200 and sum(x[0]=='put' for x in h.s3.log)==puts


def test_changed_producer_identity_is_not_replaced_by_new_head(monkeypatch,tmp_path):
    h=World();client,payload,calls=setup(h,monkeypatch,tmp_path)
    (tmp_path/'gex'/'SPY.json').write_bytes(h.gex_bytes+b' ')
    response=h.post(client,payload,token_value=token())
    assert response.status_code==200 and response.json()['status']=='unavailable'
    assert not h.s3.log


def test_partial_retention_stays_unknown_and_read_recovery_never_replays(monkeypatch,tmp_path):
    h=World();client,payload,calls=setup(h,monkeypatch,tmp_path)
    put=h.s3.put_object
    def uncertain(**kwargs):
        if kwargs['Key']==h.moves_ref.key:raise TimeoutError('controlled unknown second put')
        put(**kwargs)
    h.s3.put_object=uncertain
    response=h.post(client,payload,token_value=token())
    assert response.status_code==200 and response.json()['status']=='unavailable'
    assert h.gex_ref.key in h.s3.objects and h.moves_ref.key not in h.s3.objects
    count=len(h.s3.log)
    response=h.post(client,{**payload,'mode':'qualify'},token_value=token())
    assert response.status_code==200
    assert all(x[0]!='put' for x in h.s3.log[count:])


def test_hub_hashes_original_producer_bytes_not_reserialized_display(monkeypatch):
    raw=b'{ "schema":"options_hub.gex/v1", "root":"SPY", "asof":"2026-10-22", "spot_ref":600.0, "_scenario_source_identity":{"sha256":"spoof"} }\n'
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,*args):return raw
    monkeypatch.setattr(hub,'_HUB_CACHE',{})
    monkeypatch.setattr(hub,'_hub_r2_base',lambda:'https://controlled.invalid')
    monkeypatch.setattr(hub.urllib.request,'urlopen',lambda *args,**kwargs:Response())
    value=hub._hub_fetch('gex/SPY.json')
    identity=value['_scenario_source_identity']
    assert identity['sha256']==hashlib.sha256(raw).hexdigest() and identity['byte_length']==len(raw)
    assert identity['sha256']!=hashlib.sha256(json.dumps(value).encode()).hexdigest()
    monkeypatch.setattr(hub,'_hub_r2_base',lambda:'')
    monkeypatch.setattr(hub.time,'monotonic',lambda:10**20)
    stale=hub._hub_fetch('gex/SPY.json')
    assert stale['stale'] is True and stale['_scenario_source_identity']==identity


# Production binding composition below uses real route/auth/RLS-policy callbacks.
# Only external transports and the private-store factory are controlled doubles.
def runtime_setup(monkeypatch, tmp_path, *, capture_enabled=False, with_moves=True):
    from app import options_scenario_bindings as B
    from engine.research_vault import r2_store
    from tests.test_options_scenarios import BUCKET
    h = World()
    if not with_moves:
        original_capture = h.capture
        h.capture = lambda **kw: original_capture(**{**kw, 'with_moves': False})
    h.patch(monkeypatch)
    h.s3 = FakeS3()
    class Store(r2_store.R2Store):
        def __init__(self):
            self.bucket, self._s3 = BUCKET, h.s3
            self._single_attempt_writes = True
            self._dedicated_write_client = h.s3
        def validate_strict_conditional_write_capability(self):
            pass
        def put_bytes_strict_conditional(self, key, data, *, expected_version, content_type):
            assert expected_version is None and content_type == 'application/json'
            self._s3.put_object(Bucket=self.bucket, Key=key, Body=data,
                               ContentType=content_type, IfNoneMatch='*')
            return True
    store = Store()
    def build(**kwargs):
        assert kwargs == {'single_attempt_writes': True}
        return store
    monkeypatch.setattr(B.r2_store, 'build_store', build)
    monkeypatch.setenv('OPTIONS_SCENARIO_SOURCE_ENABLED', '1')
    monkeypatch.setenv('R2_RESEARCH_BUCKET', BUCKET)
    monkeypatch.setenv('R2_BUCKET', 'shared-public-fixture')
    monkeypatch.delenv('RESEARCH_LOCAL_STORE', raising=False)
    monkeypatch.setenv('OPTIONS_SCENARIO_CAPTURE_ENABLED', '1' if capture_enabled else '0')
    monkeypatch.setenv('OPTIONS_SCENARIO_PRODUCER_DIR', str(tmp_path))
    for kind, raw in [('gex', h.gex_bytes), ('moves', h.moves_bytes)]:
        path = tmp_path / kind / 'SPY.json'
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(raw)
    client = h.client(bind=False)
    B.install_scenario_sources(h.app)
    assert isinstance(h.app.state.options_scenario_source_bindings, B.ScenarioSourceRuntime)
    return h, client, store


def test_runtime_default_off_does_not_construct_or_contact_store(monkeypatch):
    from app import options_scenario_bindings as B
    h = World(); h.patch(monkeypatch); client = h.client(bind=False)
    monkeypatch.delenv('OPTIONS_SCENARIO_SOURCE_ENABLED', raising=False)
    monkeypatch.setattr(B.r2_store, 'build_store', lambda **kw: (_ for _ in ()).throw(AssertionError('IO')))
    B.install_scenario_sources(h.app)
    response = h.post(client, h.resolve_payload(), token_value=token())
    assert response.json()['reason'] == 'source_binding_unavailable'
    assert not h.trace


def test_runtime_refuses_public_alias_local_fallback_and_missing_producer(monkeypatch, tmp_path):
    from app import options_scenario_bindings as B
    from fastapi import FastAPI
    monkeypatch.setenv('OPTIONS_SCENARIO_SOURCE_ENABLED', '1')
    monkeypatch.setattr(B.r2_store, 'build_store', lambda **kw: (_ for _ in ()).throw(AssertionError('IO')))
    for env in [
        {'R2_RESEARCH_BUCKET':'public', 'R2_BUCKET':'public'},
        {'R2_RESEARCH_BUCKET':'private', 'RESEARCH_LOCAL_STORE':str(tmp_path)},
        {'R2_RESEARCH_BUCKET':'private','OPTIONS_SCENARIO_CAPTURE_ENABLED':'1',
         'OPTIONS_SCENARIO_PRODUCER_DIR':'relative/path'}]:
        for key in ('R2_RESEARCH_BUCKET','R2_BUCKET','RESEARCH_LOCAL_STORE',
                    'OPTIONS_SCENARIO_CAPTURE_ENABLED','OPTIONS_SCENARIO_PRODUCER_DIR'):
            monkeypatch.delenv(key, raising=False)
        for key, value in env.items(): monkeypatch.setenv(key, value)
        app = FastAPI(); B.install_scenario_sources(app)
        assert not hasattr(app.state, 'options_scenario_source_bindings')


def test_runtime_real_callbacks_capture_then_read_recovery_and_reopen(monkeypatch, tmp_path):
    h, client, store = runtime_setup(monkeypatch, tmp_path, capture_enabled=True, with_moves=False)
    monkeypatch.setattr(S, '_open_rpc', lambda *a, **kw: FakeRpcResponse({'status':'not_found'}))
    payload = {'mode':'capture','investigation_id':INV_B,'revision':1,'expected_revision':0,
               'operation_id':OP,'grant_id':None,'capture':h.capture()}
    response = h.post(client, payload, token_value=token())
    assert response.json().get('mode') == 'capture', response.text
    assert h.s3.objects[h.gex_ref.key] == h.gex_bytes
    assert h.moves_ref.key not in h.s3.objects
    count = sum(x[0] == 'put' for x in h.s3.log)
    response = h.post(client, {**payload,'mode':'qualify'}, token_value=token())
    assert response.json().get('mode') == 'qualify', response.text
    # The canonical CAS remains elsewhere; now simulate its caller-token read.
    monkeypatch.setattr(S, '_open_rpc', lambda *a, **kw: FakeRpcResponse(h.row(revision=1, inv=INV_B)))
    response = h.post(client, h.resolve_payload(revision=1, inv=INV_B), token_value=token())
    assert response.json().get('mode') == 'resolve', response.text
    assert sum(x[0] == 'put' for x in h.s3.log) == count == 1
    assert response.headers['cache-control'] == 'private, no-store'
    assert response.headers['vary'] == 'Authorization'


def test_runtime_capture_has_separate_zero_io_gate(monkeypatch, tmp_path):
    h, client, _ = runtime_setup(monkeypatch, tmp_path)
    response = h.post(client, {'mode':'capture','investigation_id':INV_B,'revision':1,
        'expected_revision':0,'operation_id':OP,'grant_id':None,'capture':h.capture()},token_value=token())
    assert response.json()['reason'] == 'source_binding_unavailable'
    assert not h.s3.log and not h.trace


def test_runtime_entitlement_and_revoked_pin_refuse_before_object_read(monkeypatch, tmp_path):
    from tests.test_options_scenarios import GRANT
    h, client, _ = runtime_setup(monkeypatch, tmp_path)
    calls = []
    def rpc(*a, **kw):
        calls.append(1)
        return FakeRpcResponse(h.handoff() if len(calls) == 1 else {'status':'not_found'})
    monkeypatch.setattr(S, '_open_rpc', rpc)
    response = h.post(client, h.resolve_payload(grant=GRANT), token_value=token())
    assert response.json()['status'] in ('denied', 'unavailable'), response.text
    assert not h.s3.log
    h.state.row = {'tier':'free','features':[]}
    response = h.post(client, h.resolve_payload(), token_value=token())
    assert response.json()['reason'] == 'product_unavailable'
    assert not h.s3.log


def test_runtime_private_transport_rejects_other_namespace_and_overwrite(monkeypatch, tmp_path):
    import pytest
    from app.options_scenario_bindings import _PrivateObjects
    h, _, store = runtime_setup(monkeypatch, tmp_path, capture_enabled=True)
    objects = _PrivateObjects(store, True)
    with pytest.raises(ValueError): objects.get_object(Bucket=store.bucket, Key='research_vault/catalog.json')
    with pytest.raises(ValueError): objects.get_object(Bucket='public', Key=h.gex_ref.key)
    with pytest.raises(ValueError): objects.put_object(Bucket=store.bucket, Key=h.gex_ref.key,
        Body=h.gex_bytes, ContentType='application/json', IfNoneMatch=None)
    assert not h.s3.log


def test_runtime_session_change_after_read_withholds_all_bytes(monkeypatch, tmp_path):
    from tests.test_options_scenarios import UID
    h, client, _ = runtime_setup(monkeypatch, tmp_path, with_moves=False)
    h.s3.objects[h.gex_ref.key] = h.gex_bytes
    h.s3.objects[h.moves_ref.key] = h.moves_bytes
    monkeypatch.setattr(S, '_open_rpc', lambda *a, **kw: FakeRpcResponse(h.row()))
    read = h.s3.get_object
    def changed(**kw):
        response = read(**kw)
        h.state.user = {**h.state.user, 'id':'cccccccc-cccc-4ccc-8ccc-cccccccccccc'}
        return response
    monkeypatch.setattr(h.s3, 'get_object', changed)
    response = h.post(client, h.resolve_payload(), token_value=token())
    assert response.json()['status'] in ('unavailable','denied'), response.text
    assert 'gex' not in response.json() and 'capture' not in response.json()


def test_runtime_uncertain_write_has_no_retry_or_false_success(monkeypatch, tmp_path):
    h, client, store = runtime_setup(monkeypatch, tmp_path, capture_enabled=True, with_moves=False)
    monkeypatch.setattr(S, '_open_rpc', lambda *a, **kw: FakeRpcResponse({'status':'not_found'}))
    calls = []
    def lost(key, data, **kw):
        calls.append(key)
        raise TimeoutError('controlled unresolved write')
    monkeypatch.setattr(store, 'put_bytes_strict_conditional', lost)
    payload = {'mode':'capture','investigation_id':INV_B,'revision':1,'expected_revision':0,
               'operation_id':OP,'grant_id':None,'capture':h.capture()}
    response = h.post(client, payload, token_value=token())
    assert response.json()['status'] == 'unavailable' and len(calls) == 1
    response = h.post(client, {**payload,'mode':'qualify'}, token_value=token())
    assert response.json()['status'] == 'unavailable' and len(calls) == 1


def test_runtime_request_scopes_do_not_borrow_actor_or_operation(monkeypatch, tmp_path):
    from app.options_auth import OptionsPrincipal
    from tests.test_options_scenarios import UID, ISS, SID
    h, _, _ = runtime_setup(monkeypatch, tmp_path, capture_enabled=True, with_moves=False)
    runtime = h.app.state.options_scenario_source_bindings
    p = OptionsPrincipal(UID, ISS, SID, 2000)
    bound = runtime.for_request(token=token(), principal=p, investigation_id=INV_B,
        revision=1, grant_id=None, capture=h.capture(), mode='capture',
        expected_revision=0, operation_id=OP)
    # A cross-request binding never acquires authority from another valid session.
    assert bound.resource_access({'viewer_id':'other'}) is False
    assert bound.source_save_decision({'operation_id':'other'})['status'] == 'denied'
    assert bound.retention_decision({'principal':'other'})['status'] == 'denied'
    assert not h.s3.log and not h.trace


def test_runtime_unqualified_whole_moves_never_inherit_named_source_attestation(monkeypatch, tmp_path):
    """Optional moves may embed the distinct Levels Yahoo grading route."""
    h, client, _ = runtime_setup(monkeypatch, tmp_path, capture_enabled=True)
    original = h.capture()
    prospective = {'investigation_id':INV_B,'revision':1,'expected_revision':0,
                   'operation_id':OP,'grant_id':None,'capture':original}
    for mode in ('capture', 'qualify', 'resolve'):
        if mode == 'resolve':
            monkeypatch.setattr(S, '_open_rpc', lambda *a, **kw: FakeRpcResponse(h.row(revision=1, inv=INV_B)))
            payload = h.resolve_payload(revision=1, inv=INV_B)
        else:
            monkeypatch.setattr(S, '_open_rpc', lambda *a, **kw: FakeRpcResponse({'status':'not_found'}))
            payload = {**prospective, 'mode':mode}
        response = h.post(client, payload, token_value=token())
        assert response.json().get('status') == 'unavailable', (mode, response.text)
        assert response.json().get('reason') == 'source_unavailable', (mode, response.text)
        assert not h.s3.log, (mode, h.s3.log)
        assert h.capture() == original and original['source']['moves'] is not None
