"""One recomputed-history catalogue in the existing International workspace."""
from copy import deepcopy

from lib.intl_macro_mount import _bound, _contexts, _registry, _validate_config
from lib.intl_workspace_binding import binding_version
from lib.intl_workspace_history import build_history_section


def _unknown_source():
    return dict(
        history_read=dict(status='missing',market_id=None,artifact_ref=None,read_at=None,
                          method_ref=None,identity=None,points=[]),
        turn_events=[],track_record=None,destinations={},
        capabilities={**{key:dict(metadata='unknown',value='unknown')
                         for key in ('history_source','events','track_record')},
                      'snapshot_compare':dict(left_observation_at=None,right_observation_at=None)},
    )


def attach_history(workspace, *, registry, sources):
    """Project already supplied receipts once per market; never read or grant.

    History is the full supplied reconstruction, independent of the return
    horizon and currency toolbar. The sole controller may adapt those two panel
    presentation attributes; it must not filter, annualize or relabel the scores.
    """
    if workspace is None:
        return None
    try:
        for value in (workspace,registry,sources):
            _bound(value)
        if type(workspace) is not dict or 'histories' in workspace or 'history_registry' in workspace:
            raise ValueError
        _validate_config(workspace.get('config'))
        version,generation=binding_version(workspace)
        markets=_registry(registry,workspace['config'])
        contexts=_contexts(workspace['panels'],workspace['config'],version,generation)
        if 'im-history' in contexts or type(sources) is not dict or not set(sources)<=set(markets):
            raise ValueError
        context=dict(horizon=workspace['config']['default_horizon'],
                     currency_basis=workspace['config']['default_basis'],return_basis='price')
        sections=[]
        for market in markets:
            source=sources.get(market,_unknown_source())
            if type(source) is not dict or set(source)!={'history_read','turn_events','track_record','capabilities','destinations'}:
                raise ValueError
            if source['history_read']['market_id'] not in {None,market}:
                raise ValueError
            selected={**context,'selected_market':market}
            section=build_history_section(context=selected,**source)
            if version==1:
                capabilities=deepcopy(source['capabilities'])
                for key in ('history_source','events','track_record'):
                    capabilities[key]=dict(metadata='unknown',value='unknown')
                section=build_history_section(context=selected,**{**source,'capabilities':capabilities})
            sections.append(section)
        result=deepcopy(workspace)
        result['histories']=[dict(context_id='im-history',context=context,sections=sections,
                                 source_reference=workspace['config']['source_reference'] if version==1 else None,
                                 **({'generation':generation} if version==2 else {}))]
        result['history_registry']=deepcopy(registry)
        return result
    except (ValueError,TypeError,KeyError,OverflowError,RecursionError):
        raise ValueError('invalid_history_workspace') from None
