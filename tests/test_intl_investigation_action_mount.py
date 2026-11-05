"""Native generation preparation without current-pointer activation."""
from copy import deepcopy
import hashlib,json
import pytest
from lib.intl_generation_publication import publish_unavailable_generation,publish_generation,read_generation_publication
from lib.intl_investigation_action_mount import prepare_investigation_actions
from tests.test_intl_generation_publication import _build,GENERATION

def workspace():
    panel={'generation':GENERATION,'context':{'horizon':'1m','currency_basis':'local'}}
    return {'config':{'source_reference':GENERATION},'macros':[deepcopy(panel)],'risks':[deepcopy(panel)]}

def test_prepared_actual_immutable_dependencies_do_not_activate_current(tmp_path):
    publish_unavailable_generation(data_root=tmp_path)
    pointer=tmp_path/'intl/publication/generations/intl_generation_current.json';before=pointer.read_bytes()
    original=workspace();snapshot=deepcopy(original)
    mounted,contract=prepare_investigation_actions(original,data_root=tmp_path,contract=_build())
    assert original==snapshot and pointer.read_bytes()==before
    assert read_generation_publication(data_root=tmp_path)['status']=='unavailable'
    for view in ('macros','risks'):
        actions=mounted[view][0]['investigation_actions']
        assert 'EZ.policy_rate'in actions and 'JP.cpi_yoy'not in actions
        action=actions['EZ.policy_rate'];assert action['field_ids']==['EZ.policy_rate']
        raw=json.dumps(contract,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        assert action['fingerprint']==hashlib.sha256(raw).hexdigest()
    descriptor=publish_generation(data_root=tmp_path,contract=contract)
    assert descriptor['artifact_sha256']==mounted['macros'][0]['investigation_actions']['EZ.policy_rate']['fingerprint']
    assert read_generation_publication(data_root=tmp_path)['status']=='ready'

@pytest.mark.parametrize('fault',['workspace','panel'])
def test_wrong_generation_emits_no_actions_and_never_advances_pointer(tmp_path,fault):
    publish_unavailable_generation(data_root=tmp_path);before=(tmp_path/'intl/publication/generations/intl_generation_current.json').read_bytes()
    w=workspace()
    if fault=='workspace':w['config']['source_reference']='foreign'
    else:w['macros'][0]['generation']='foreign'
    with pytest.raises(ValueError):prepare_investigation_actions(w,data_root=tmp_path,contract=_build())
    assert all('investigation_actions'not in p for p in w['macros'])
    assert (tmp_path/'intl/publication/generations/intl_generation_current.json').read_bytes()==before


def test_wrong_context_has_no_enabled_field_action(tmp_path):
    w=workspace();w['macros'][0]['context']['horizon']='unregistered'
    mounted,_=prepare_investigation_actions(w,data_root=tmp_path,contract=_build())
    assert mounted['macros'][0]['investigation_actions']=={}
