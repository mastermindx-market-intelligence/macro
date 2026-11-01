from copy import deepcopy
import json
from pathlib import Path
import pytest
from lib.intl_history_mount import attach_history

GENERATION='im-workspace-generation:12345678-1234-4123-8123-123456789012'

def fixture():
    args=deepcopy(json.loads((Path(__file__).parent/'fixtures/intl_workspace/history_cases.json').read_text())['cases'][0]['args'])
    config=dict(markets=['JP','KR'],horizons=['1m','3m'],bases=['local','usd_unhedged'],default_horizon='1m',default_basis='usd_unhedged',source_reference=GENERATION,anchor_ids=[],library_group_ids=[])
    workspace=dict(binding_version=2,config=config,panels=[dict(context_id='im-'+str(i),generation=GENERATION,overview=dict(context=dict(horizon=h,currency_basis=b,return_basis='price',source_reference=None,source_reference_reason='not_supplied'))) for i,(h,b) in enumerate((h,b) for h in config['horizons'] for b in config['bases'])],existing_material={'kept':True})
    registry=dict(markets=[dict(market_id=x,name_en=x,name_zh=x) for x in config['markets']],horizons=config['horizons'],bases=config['bases'])
    args.pop('context')
    return workspace,dict(registry=registry,sources={'JP':args})

def test_one_catalogue_joins_real_helper_once_per_market_without_context_duplication():
    w,args=fixture(); before=deepcopy((w,args)); result=attach_history(w,**args)
    assert len(result['histories'])==1
    p=result['histories'][0];assert p['generation']==GENERATION and p['context_id']=='im-history'
    assert p['context']==dict(horizon='1m',currency_basis='usd_unhedged',return_basis='price')
    assert [s['selected_market'] for s in p['sections']]==['JP','KR']
    assert p['sections'][0]['source_read_status']=='ready'
    assert p['sections'][0]['points'][0]['growth_score']==args['sources']['JP']['history_read']['points'][0]['growth_score']
    assert p['sections'][1]['source_read_status']=='unknown'
    assert p['sections'][1]['points']==[]
    assert result['existing_material']==w['existing_material']
    assert (w,args)==before
    result['histories'][0]['sections'][0]['points'][0]['growth_score']=999
    assert (w,args)==before

def test_v1_cannot_admit_new_history_values_or_sidecar_generation():
    w,args=fixture();w.pop('binding_version');w['config']['source_reference']=None
    for p in w['panels']:p.pop('generation')
    result=attach_history(w,**args);p=result['histories'][0]
    assert 'generation' not in p
    assert all(x['source_read_status']=='unknown' and x['points']==[] for x in p['sections'])
    assert all(x['events']['records']==[] and x['track_record']['graded_count'] is None for x in p['sections'])

@pytest.mark.parametrize('change',[
 lambda w,a:a['sources'].update(US=a['sources']['JP']),
 lambda w,a:a['sources']['JP']['history_read'].update(market_id='KR'),
 lambda w,a:a['registry']['markets'].reverse(),
 lambda w,a:w.update(histories=[]),
 lambda w,a:w.update(history_registry={}),
 lambda w,a:w['panels'][0].update(context_id='im-history'),
 lambda w,a:w['panels'].pop(),
 lambda w,a:w['panels'][0].update(generation='other'),
 lambda w,a:a['sources']['JP'].update(context={}),
 lambda w,a:a['sources']['JP']['capabilities']['history_source'].update(metadata='denied',value='allowed'),
 lambda w,a:a['sources']['JP']['history_read']['identity'].update(return_basis='total_return'),
 lambda w,a:w['config'].update(default_horizon='12m'),
])
def test_bad_mount_refuses_atomically_with_fixed_error(change):
    w,args=fixture();change(w,args);before=deepcopy((w,args))
    with pytest.raises(ValueError,match='^invalid_history_workspace$'):attach_history(w,**args)
    assert (w,args)==before

def test_failed_read_does_not_become_empty_or_hide_independently_allowed_events():
    w,args=fixture();args['sources']['JP']['history_read'].update(status='failed',identity=None,points=[])
    p=attach_history(w,**args)['histories'][0]['sections'][0]
    assert p['source_read_status']=='failed' and p['points']==[]
    assert p['events']['status']=='available'

def test_absent_workspace_remains_absent():
    assert attach_history(None,registry={},sources={}) is None

def test_cyclic_input_never_enters_public_output():
    w,args=fixture();w['existing_material']['cycle']=w
    with pytest.raises(ValueError,match='^invalid_history_workspace$'):attach_history(w,**args)

def test_shared_binding_owner_checks_the_new_history_sidecar():
    from lib.intl_workspace_binding import binding_version
    w,args=fixture(); result=attach_history(w,**args)
    assert binding_version(result)==(2,GENERATION)
    result['histories'][0]['generation']='mismatch'
    with pytest.raises(ValueError):binding_version(result)

def test_v1_nonnull_presentation_source_is_retained_without_values():
    w,args=fixture();w.pop('binding_version');w['config']['source_reference']='legacy:fixture'
    for panel in w['panels']:
        panel.pop('generation');panel['overview']['context']['source_reference']='legacy:fixture'
    result=attach_history(w,**args)
    assert result['histories'][0]['source_reference']=='legacy:fixture'
    assert all(s['points']==[] for s in result['histories'][0]['sections'])
