"""Independent pressure clocks and field identity must survive the projection."""
from copy import deepcopy
import json
import pytest
from lib.intl_workspace_risk_pressure import build_pressure_rows


def inputs():
    registry={'markets':[{'market_id':'JP','name_en':'Japan','name_zh':'日本'}, {'market_id':'TW','name_en':'Taiwan','name_zh':'台湾'}], 'horizons':['1m'], 'bases':['local','usd_unhedged']}
    fields={}; support={}
    specs=[('country_credit_change','bp','country_credit_spread',0),('constituent_breadth_50d','percent','constituent_breadth',61),('annual_current_account','percent_gdp','current_account',3.4)]
    for field,unit,kind,value in specs:
        fields['JP.'+field]={'quality':'qualified','reason':None,'metadata':'allowed','value_permission':'allowed','value':value,'unit':unit,'instrument':{'kind':kind,'id':'native-'+field,'market_id':'JP'},'period':None,'observation_at':'2026-10-07','calculation_at':None,'source_reference':'public-source','evidence_key':'public-'+field}
    fields['JP.country_credit_change']['period']={'start':'2026-09-09','end':'2026-10-07','count':20,'count_basis':'sessions'}
    support['JP.country_credit_change']={'method_ref':'credit-owner','scope':'country','instrument_id':'native-country_credit_change','market_id':'JP','change_start':'2026-09-09','change_end':'2026-10-07'}
    support['JP.constituent_breadth_50d']={'method_ref':'breadth-owner','market_id':'JP','index_id':'native-constituent_breadth_50d','membership_asof':'2026-10-07','membership_ref':'public-members','eligible_count':100,'above_count':61,'lookback_sessions':50}
    fields['JP.annual_current_account']['period']={'start':'2024-01-01','end':'2025-01-01','count':1,'count_basis':'release_periods'}
    support['JP.annual_current_account']={'method_ref':'annual-owner','market_id':'JP','field_year':2024,'vintage':'2026-10-01','observation_type':'actual'}
    return dict(registry=registry,measures=fields,field_support=support)


def field(obj,name):return build_pressure_rows(**obj)[0][name]


def test_three_positive_fields_keep_native_values_and_each_clock():
    obj=inputs();out=build_pressure_rows(**obj)
    assert [x['market_id'] for x in out]==['JP','TW']
    assert out[0]['country_credit_change']['value']==0
    assert out[0]['constituent_breadth_50d']['value']==61
    assert out[0]['annual_current_account']['value']==3.4
    assert out[0]['annual_current_account']['support']['field_year']==2024
    assert out[0]['country_credit_change']['period']['count']==20
    assert out[1]['annual_current_account']=={'field':'annual_current_account','quality':'unknown','reason':'not_supplied'}


@pytest.mark.parametrize('kind',['actual','estimate','projection'])
def test_annual_type_is_never_upgraded_to_observed(kind):
    obj=inputs();obj['field_support']['JP.annual_current_account']['observation_type']=kind
    out=field(obj,'annual_current_account')
    assert out['quality']=='qualified' and out['support']['observation_type']==kind


@pytest.mark.parametrize('which',['country_credit_change','annual_current_account'])
@pytest.mark.parametrize('value',[-12.25,0])
def test_signed_and_zero_are_not_safety_or_missing(which,value):
    obj=inputs();obj['measures']['JP.'+which]['value']=value
    assert field(obj,which)['value']==value


@pytest.mark.parametrize('metadata',['denied','unknown'])
def test_denied_metadata_hides_every_field_detail(metadata):
    obj=inputs();m=obj['measures']['JP.country_credit_change'];m.update(metadata=metadata,value=345,source_reference='SECRET',reason='SECRET')
    out=field(obj,'country_credit_change')
    assert set(out)=={'field','quality','reason'} and out['quality']!='qualified'
    assert 'SECRET' not in json.dumps(out) and '345' not in json.dumps(out)


def test_value_denied_cannot_preserve_qualified_label_or_number():
    obj=inputs();obj['measures']['JP.country_credit_change']['value_permission']='denied'
    out=field(obj,'country_credit_change')
    assert out['value'] is None and out['quality']=='denied' and out['reason']=='value_denied'


@pytest.mark.parametrize('part,value',[('scope','regional'),('market_id','TW'),('change_end','2026-10-06'),('instrument_id','EM-OAS')])
def test_regional_or_wrong_interval_credit_never_becomes_country_reading(part,value):
    obj=inputs();obj['field_support']['JP.country_credit_change'][part]=value
    out=field(obj,'country_credit_change')
    assert out=={'field':'country_credit_change','quality':'unknown','reason':'support_unavailable'}
    assert field(obj,'annual_current_account')['value']==3.4


def test_actual_nonstandard_credit_period_remains_honest():
    obj=inputs();obj['measures']['JP.country_credit_change']['period']['count']=19
    assert field(obj,'country_credit_change')['period']['count']==19


@pytest.mark.parametrize('part,value',[('eligible_count',0),('eligible_count',True),('above_count',101),('above_count',True),('lookback_sessions',200),('membership_asof','2026-10-08'),('index_id','bellwether-sample'),('market_id','TW'),('membership_ref','')])
def test_breadth_requires_real_denominator_membership_clock_and_identity(part,value):
    obj=inputs();obj['field_support']['JP.constituent_breadth_50d'][part]=value
    out=field(obj,'constituent_breadth_50d')
    assert out['quality']=='unknown' and out.get('value') is None


def test_breadth_does_not_repair_owner_percentage():
    obj=inputs();obj['measures']['JP.constituent_breadth_50d']['value']=60
    assert field(obj,'constituent_breadth_50d')['quality']=='unknown'


@pytest.mark.parametrize('part,value',[('field_year',2025),('field_year',True),('field_year',9999),('market_id','CN'),('vintage','2026-02-30'),('observation_type','max_asof_year')])
def test_annual_field_year_and_vintage_are_specific_not_row_max(part,value):
    obj=inputs();obj['field_support']['JP.annual_current_account'][part]=value
    out=field(obj,'annual_current_account')
    assert out['quality']=='unknown' and out.get('value') is None


def test_stale_value_stays_stale_with_original_value():
    obj=inputs();obj['measures']['JP.country_credit_change']['quality']='stale'
    out=field(obj,'country_credit_change')
    assert out['quality']=='stale' and out['value']==0 and out['reason']=='source_stale'


def test_bad_cell_does_not_remove_good_neighbor_or_roster():
    obj=inputs();obj['measures']['JP.country_credit_change']={'secret':'SECRET'}
    out=build_pressure_rows(**obj)
    assert len(out)==2 and out[0]['annual_current_account']['value']==3.4
    assert out[0]['country_credit_change']['quality']=='unknown'


def test_deep_detachment_and_no_input_mutation():
    obj=inputs();old=deepcopy(obj);out=build_pressure_rows(**obj)
    out[0]['annual_current_account']['support']['field_year']=1
    out[0]['country_credit_change']['period']['count']=1
    assert obj==old


@pytest.mark.parametrize('key',['unknown.field','CN.country_credit_change','JP.bad_field'])
def test_unknown_input_identity_is_fixed_error(key):
    obj=inputs();obj['measures'][key]={}
    with pytest.raises(ValueError,match='^invalid_risk_pressure_input$'):build_pressure_rows(**obj)


def test_hostile_and_cyclic_trees_do_not_execute_hooks():
    class Hostile(dict):
        def get(self,*a):raise AssertionError('ran hook')
    obj=inputs();obj['measures']=Hostile(obj['measures'])
    with pytest.raises(ValueError,match='^invalid_risk_pressure_input$'):build_pressure_rows(**obj)
    obj=inputs();obj['measures']['self']=obj
    with pytest.raises(ValueError,match='^invalid_risk_pressure_input$'):build_pressure_rows(**obj)


def test_finite_integer_is_not_rejected_by_float_coercion():
    obj=inputs();obj['measures']['JP.country_credit_change']['value']=10**400
    assert field(obj,'country_credit_change')['value']==10**400


def test_future_annual_period_is_not_an_actual_observation():
    obj=inputs();obj['field_support']['JP.annual_current_account']['field_year']=2027
    obj['measures']['JP.annual_current_account']['period'].update(start='2027-01-01',end='2028-01-01')
    assert field(obj,'annual_current_account')['quality']=='unknown'
    obj['field_support']['JP.annual_current_account']['observation_type']='projection'
    assert field(obj,'annual_current_account')['quality']=='qualified'
