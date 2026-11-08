"""Actual ingress/producer composition with controlled private store + RPC only."""
from dataclasses import replace
from copy import deepcopy
import pytest
from tests.test_options_scenarios import World, token, OP
from tests.test_scenario_initial_capture import setup


@pytest.mark.parametrize('change', ['actor', 'target', 'revision', 'action', 'reference', 'boolean', 'missing', 'layout'])
def test_canonical_original_request_substitutions_refuse_before_claim_or_put(monkeypatch,tmp_path,change):
    h=World();client,payload,_=setup(h,monkeypatch,tmp_path)
    request=deepcopy(payload['canonical_request'])
    if change=='actor':request['principal']='20000000-0000-4000-8000-000000000002'
    elif change=='target':request['target']=OP
    elif change=='revision':request['expected_revision']=1
    elif change=='action':request['action']='revise'
    elif change=='reference':request['manifest']['scenario_capture']['source']['gex']['sha256']='f'*64
    elif change=='boolean':request['manifest']['scenario_capture']['inputs']['days']=False
    elif change=='layout':request['layout_capture']={'layout_id':OP,'expected_revision':True,'revision_id':OP}
    else:request.pop('layout_capture')
    response=h.post(client,{**payload,'canonical_request':request},token_value=token())
    assert response.json()['status']=='unavailable'
    assert not h.native_rpc_calls and not h.s3.log


def test_claim_precedes_every_put_and_completion_follows_all_original_writes(monkeypatch,tmp_path):
    h=World(); client,payload,_=setup(h,monkeypatch,tmp_path)
    original=h.s3.put_object
    def put(**kwargs):
        assert h.native_phases[OP]['state']=='started'
        h.trace.append(('put',kwargs['Key']))
        return original(**kwargs)
    h.s3.put_object=put
    response=h.post(client,payload,token_value=token())
    assert response.json()['native_capture']['native_phase']=='retained'
    names=[event[0] for event in h.trace]
    assert names.index('native_claim')<names.index('put')<names.index('native_complete')
    assert all(name!='put' for name in names[names.index('native_complete')+1:])
    assert [kind for kind,_ in h.native_rpc_calls]==['claim','complete']


def test_same_original_operation_never_captures_twice_even_when_content_exists(monkeypatch,tmp_path):
    h=World();client,payload,_=setup(h,monkeypatch,tmp_path)
    assert h.post(client,payload,token_value=token()).json()['status']=='resolved'
    puts=sum(x[0]=='put' for x in h.s3.log)
    assert h.post(client,payload,token_value=token()).json()['status']=='unavailable'
    assert sum(x[0]=='put' for x in h.s3.log)==puts
    assert [kind for kind,_ in h.native_rpc_calls]==['claim','complete','claim']
    # Same key with changed requested scenario is a conflict, never recapture.
    changed={**payload,'capture':{**payload['capture'],'inputs':{**payload['capture']['inputs'],'targetSpot':601}}}
    assert h.post(client,changed,token_value=token()).json()['status']=='unavailable'
    assert sum(x[0]=='put' for x in h.s3.log)==puts


def test_lost_claim_ack_never_starts_a_put_or_automatically_retries(monkeypatch,tmp_path):
    h=World();client,payload,_=setup(h,monkeypatch,tmp_path);h.native_lost_ack='claim'
    assert h.post(client,payload,token_value=token()).json()['status']=='unavailable'
    assert h.native_phases[OP]['state']=='started' # fixture models possible committed claim
    assert not h.s3.log and len(h.native_rpc_calls)==1
    h.native_lost_ack=None
    assert h.post(client,payload,token_value=token()).json()['status']=='unavailable'
    assert not h.s3.log and len(h.native_rpc_calls)==2


def test_partial_store_effect_never_records_retained_or_replays_original(monkeypatch,tmp_path):
    h=World();client,payload,_=setup(h,monkeypatch,tmp_path)
    original=h.s3.put_object
    def partial(**kwargs):
        if kwargs['Key']==h.moves_ref.key:raise TimeoutError('controlled unresolved second send')
        return original(**kwargs)
    h.s3.put_object=partial
    assert h.post(client,payload,token_value=token()).json()['status']=='unavailable'
    assert h.gex_ref.key in h.s3.objects and h.moves_ref.key not in h.s3.objects
    assert h.native_phases[OP]['state']=='started'
    assert [kind for kind,_ in h.native_rpc_calls]==['claim']
    count=len(h.s3.log)
    assert h.post(client,payload,token_value=token()).json()['status']=='unavailable'
    assert len(h.s3.log)==count


def test_lost_completion_ack_leaves_caller_unknown_and_duplicate_put_suppressed(monkeypatch,tmp_path):
    h=World();client,payload,_=setup(h,monkeypatch,tmp_path);h.native_lost_ack='complete'
    assert h.post(client,payload,token_value=token()).json()['status']=='unavailable'
    assert h.native_phases[OP]['state']=='retained' # fixture state is not caller proof
    puts=sum(x[0]=='put' for x in h.s3.log)
    assert [kind for kind,_ in h.native_rpc_calls]==['claim','complete']
    h.native_lost_ack=None
    assert h.post(client,payload,token_value=token()).json()['status']=='unavailable'
    assert sum(x[0]=='put' for x in h.s3.log)==puts


def test_late_original_phase_completion_does_not_reopen_capture_admission(monkeypatch,tmp_path):
    from app import options_scenarios as S
    h=World();client,payload,_=setup(h,monkeypatch,tmp_path)
    original=S._producer.capture_built_scenario_sources
    def original_finishes(*args,**kwargs):
        result=original(*args,**kwargs)
        current=h.app.state.options_scenario_source_bindings
        h.app.state.options_scenario_source_bindings=replace(current,producer_out_dir=None)
        return result
    monkeypatch.setattr(S._producer,'capture_built_scenario_sources',original_finishes)
    response=h.post(client,payload,token_value=token())
    assert response.json()['native_capture']['native_phase']=='retained'
    count=len(h.s3.log)
    assert h.post(client,payload,token_value=token()).json()['reason']=='source_binding_unavailable'
    assert len(h.s3.log)==count and len(h.native_rpc_calls)==2


def test_browser_cannot_supply_a_completion_or_server_binding(monkeypatch,tmp_path):
    h=World();client,payload,_=setup(h,monkeypatch,tmp_path)
    response=h.post(client,{**payload,'native_capture':{'status':'recorded','native_phase':'retained'}},token_value=token())
    assert response.json()['reason']=='request_invalid'
    assert not h.native_rpc_calls and not h.s3.log
