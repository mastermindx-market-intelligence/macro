"""Compose source-bound actions into the incumbent International page.

Preparation writes immutable feed dependencies only. It never advances the
current selector; the normal publisher does that after both page writes.
"""
from copy import deepcopy
import hashlib
from urllib.parse import urlencode
from lib.intl_generation_publication import (
    serialize_generation, _generations_dir, _write_immutable, _canonical_json,
    _validate_descriptor, _verify_policy_points, MAX_ARTIFACT_BYTES, MAX_DESCRIPTOR_BYTES,
)


def prepare_investigation_actions(workspace, *, data_root, contract, policy_points=None):
    """Return action-mounted page + exact prepared contract without activation."""
    from lib.intl_investigation_action import build_intl_investigation_action
    from lib.intl_policy_publication import publish_policy_points
    if (type(workspace)is not dict or type(contract)is not dict
            or workspace.get('config',{}).get('source_reference')!=contract.get('generation')):
        raise ValueError('investigation generation differs from rendered workspace')
    result=deepcopy(workspace);prepared=deepcopy(contract)
    if policy_points is not None:
        if policy_points.get('generation')!=prepared['generation']:
            raise ValueError('policy points differ from workspace generation')
        prepared['policy_points_ref']=publish_policy_points(data_root=data_root,contract=policy_points)
    raw=serialize_generation(prepared);digest=hashlib.sha256(raw).hexdigest()
    name='intl_generation_'+prepared['generation'].split(':',1)[1]+'_'+digest+'.json'
    descriptor={'schema':'intl.workspace_generation_current.v1','asof':None,'state':'ready',
        'generation':prepared['generation'],'artifact_name':name,'artifact_sha256':digest,
        'artifact_bytes':len(raw),'current_policies':deepcopy(prepared['policies'])}
    directory=_generations_dir(data_root,create=True)
    if prepared.get('policy_points_ref') is not None:
        _verify_policy_points(directory,prepared['policy_points_ref'],prepared['generation'])
        descriptor['current_policy_points']={'metadata':'allowed','value_permission':'allowed',
            'mapping_identity':prepared['policy_points_ref']['mapping_identity']}
    _validate_descriptor(descriptor)
    _write_immutable(directory/name,raw,MAX_ARTIFACT_BYTES)
    witness=_canonical_json(descriptor).encode()
    _write_immutable(directory/('intl_generation_descriptor_'+hashlib.sha256(witness).hexdigest()+'.json'),witness,MAX_DESCRIPTOR_BYTES)
    # No current-pointer write here. These are actual immutable dependencies,
    # ready for the normal page-then-current publication commit.
    for view,panels in [('macro',result.get('macros',[])),('risk',result.get('risks',[]))]:
        for panel in panels:
            if panel.get('generation')!=prepared['generation']:
                raise ValueError('panel generation differs from investigation source')
            context=panel.get('context',{});actions={}
            for native in prepared['contexts']:
                if native['horizon']!=context.get('horizon') or native['currency_basis']!=context.get('currency_basis'):
                    continue
                return_url='https://www.mastermind-x.com/intl.html?'+urlencode({
                    'view':view,'market':native['market'],'pins':'','horizon':native['horizon'],
                    'basis':native['currency_basis'],'return_basis':'price','group':''})
                for sid in native['measure_ids']:
                    action=build_intl_investigation_action(contract=prepared,descriptor=descriptor,
                        context_id=native['id'],selected_measure_ids=[sid],return_url=return_url)
                    if action is not None:actions[sid]=action
            panel['investigation_actions']=actions
    return result,prepared
