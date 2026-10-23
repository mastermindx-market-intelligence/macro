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
