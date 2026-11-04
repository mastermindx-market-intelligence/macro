"""Closed Eurostat EA21 annual statistical-period support for the pressure projection."""
from copy import deepcopy
import json
import pytest
from lib.intl_workspace_risk_pressure import build_pressure_rows

_INSTRUMENT_ID = 'TIPSBP20/A/PC_GDP/CA/S1/S1/BAL/EXT_EA21/NSA/EA21'
_METHOD_REF = 'docs/INTERNATIONAL_MACRO_DATA_CONTRACT.md#official-eurostat-ea21-annual-current-account'
_SUPPORT_KEYS = {'method_ref','market_id','field_year','vintage','observation_type',
                 'observation_clock_basis','dataset_updated_at'}
_LEGACY_KEYS = {'method_ref','market_id','field_year','vintage','observation_type'}


def inputs():
    """One qualified Eurostat EA21 annual current-account statistical cell."""
    registry={'markets':[{'market_id':'EZ','name_en':'Euro area','name_zh':'欧元区'}],
              'horizons':['1m'],'bases':['local']}
    measure={'quality':'qualified','reason':None,'metadata':'allowed','value_permission':'allowed',
             'value':1.7,'unit':'percent_gdp',
             'instrument':{'kind':'current_account','id':_INSTRUMENT_ID,'market_id':'EZ'},
             'period':{'start':'2025-01-01','end':'2026-01-01','count':1,'count_basis':'release_periods'},
             'observation_at':'2025-12-31','calculation_at':None,
             'source_reference':'eurostat-bop-annual','evidence_key':'eurostat-ea21-ca-2025'}
    support={'method_ref':_METHOD_REF,'market_id':'EZ','field_year':2025,'vintage':None,
             'observation_type':'statistical','observation_clock_basis':'period_end',
             'dataset_updated_at':'2026-10-28T23:00:00+0100'}
    return dict(registry=registry,measures={'EZ.annual_current_account':measure},
                field_support={'EZ.annual_current_account':support})


def field(obj,name='annual_current_account'):
    return build_pressure_rows(**obj)[0][name]


def refused(obj,name='annual_current_account'):
    out=field(obj,name)
    assert out['quality']=='unknown' and out.get('value') is None and 'support' not in out
    return out


def test_root_actual_shape_keeps_its_value_and_closed_seven_key_support():
    out=field(inputs())
    assert out['quality']=='qualified' and out['value']==1.7 and out['unit']=='percent_gdp'
    assert out['observation_at']=='2025-12-31' and out['calculation_at'] is None
    assert out['period']=={'start':'2025-01-01','end':'2026-01-01','count':1,'count_basis':'release_periods'}
    support=out['support']
    assert set(support)==_SUPPORT_KEYS
    assert support['field_year']==2025
    assert support['vintage'] is None
    assert support['observation_type']=='statistical'
    assert support['observation_clock_basis']=='period_end'
    assert support['market_id']=='EZ'
    assert support['method_ref']==_METHOD_REF
    assert support['dataset_updated_at']=='2026-10-28T23:00:00+0100'


@pytest.mark.parametrize('value',[0,-1.7,12.5,-0.0])
def test_zero_and_signed_statistical_values_are_kept(value):
    obj=inputs();obj['measures']['EZ.annual_current_account']['value']=value
    out=field(obj)
    assert out['quality']=='qualified' and out['value']==value


def test_absent_vintage_stays_absent_and_is_never_backfilled():
    out=field(inputs())
    assert out['support']['vintage'] is None
    assert out['support']['observation_type']=='statistical'
    assert out['calculation_at'] is None
    assert out['observation_at']=='2025-12-31'


def test_dataset_updated_at_is_independent_of_the_observation_and_the_value():
    obj=inputs()
    obj['field_support']['EZ.annual_current_account']['dataset_updated_at']='2027-03-01T00:00:00+0000'
    out=field(obj)
    assert out['value']==1.7
    assert out['observation_at']=='2025-12-31'
    assert out['calculation_at'] is None
    assert out['support']['vintage'] is None
    assert out['support']['dataset_updated_at']=='2027-03-01T00:00:00+0000'


def test_statistical_cell_is_never_labelled_actual_estimate_or_projection():
    out=field(inputs())
    assert out['support']['observation_type']=='statistical'
    flat=json.dumps(out)
    assert '"actual"' not in flat and '"estimate"' not in flat and '"projection"' not in flat


@pytest.mark.parametrize('identifier',[
    'TIPSBP20/A/PC_GDP/CA/S1/S1/BAL/EXT_EA21/NSA/EA20',
    'TIPSBP20/A/PC_GDP/CA/S1/S1/BAL/EXT_EA20/NSA/EA21',
    'TIPSBP20/A/PC_GDP/CA/S1/S1/BAL/EXT_EA21/SA/EA21',
    'TIPSBP20/A/PC_GDP/CA/S1/S1/BAL/EXT_EA21/NSA/EA21/EXTRA',
    'eurostat-current-account',
])
def test_only_the_exact_eurostat_ea21_instrument_is_accepted(identifier):
    obj=inputs();obj['measures']['EZ.annual_current_account']['instrument']['id']=identifier
    refused(obj)


def test_wrong_instrument_kind_or_market_is_refused():
    obj=inputs();obj['measures']['EZ.annual_current_account']['instrument']['kind']='gdp_yoy'
    refused(obj)
    obj=inputs();obj['measures']['EZ.annual_current_account']['instrument']['market_id']='JP'
    refused(obj)


@pytest.mark.parametrize('method',[
    'docs/INTERNATIONAL_MACRO_DATA_CONTRACT.md#official-eurostat-ea21-quarterly-current-account',
    'docs/INTERNATIONAL_MACRO_DATA_CONTRACT.md',
    'eurostat-bop',
    '',
])
def test_only_the_exact_method_ref_is_accepted(method):
    obj=inputs();obj['field_support']['EZ.annual_current_account']['method_ref']=method
    refused(obj)


@pytest.mark.parametrize('basis',['publication','as_of','period_start','release','',None])
def test_only_the_period_end_clock_basis_is_accepted(basis):
    obj=inputs();obj['field_support']['EZ.annual_current_account']['observation_clock_basis']=basis
    refused(obj)


def test_statistical_variant_is_not_a_generic_relaxation_for_another_country():
    obj=inputs()
    obj['registry']['markets']=[{'market_id':'JP','name_en':'Japan','name_zh':'日本'}]
    measure=obj['measures'].pop('EZ.annual_current_account')
    measure['instrument']={'kind':'current_account','id':_INSTRUMENT_ID,'market_id':'JP'}
    obj['measures']['JP.annual_current_account']=measure
    support=obj['field_support'].pop('EZ.annual_current_account')
    support['market_id']='JP'
    obj['field_support']['JP.annual_current_account']=support
    refused(obj)


def test_statistical_shape_cannot_enter_another_field():
    obj=inputs()
    obj['measures']['EZ.country_credit_change']={
        'quality':'qualified','reason':None,'metadata':'allowed','value_permission':'allowed',
        'value':0,'unit':'bp',
        'instrument':{'kind':'country_credit_spread','id':'native-country_credit_change','market_id':'EZ'},
        'period':{'start':'2026-09-09','end':'2026-10-07','count':20,'count_basis':'sessions'},
        'observation_at':'2026-10-07','calculation_at':None,
        'source_reference':'public-source','evidence_key':'public-credit'}
    obj['field_support']['EZ.country_credit_change']=deepcopy(obj['field_support']['EZ.annual_current_account'])
    refused(obj,'country_credit_change')


@pytest.mark.parametrize('vintage',['2026-10-01','2026-10-01T00:00:00+0100',20261001])
def test_a_supplied_vintage_is_refused_by_the_statistical_variant(vintage):
    obj=inputs();obj['field_support']['EZ.annual_current_account']['vintage']=vintage
    refused(obj)


@pytest.mark.parametrize('key',sorted(_SUPPORT_KEYS))
def test_every_statistical_support_key_is_required(key):
    obj=inputs();del obj['field_support']['EZ.annual_current_account'][key]
    refused(obj)


def test_an_extra_statistical_support_key_is_refused():
    obj=inputs();obj['field_support']['EZ.annual_current_account']['estimate']=False
    refused(obj)


@pytest.mark.parametrize('stamp',[
    '2026-10-28T23:00:00',
    '2026-10-28',
    '2026-10-28 23:00:00+0100',
    '2026-10-28T23:00:00+0100x',
    '2026-10-28T23:00:00+01',
    '2026-10-28T23:00',
    '2026-13-28T23:00:00+0100',
    '2026-10-28T25:00:00+0100',
    'not-a-timestamp',
    '',
])
def test_dataset_updated_at_must_be_an_offset_aware_timestamp(stamp):
    obj=inputs();obj['field_support']['EZ.annual_current_account']['dataset_updated_at']=stamp
    refused(obj)


@pytest.mark.parametrize('stamp',[
    '2025-12-30T23:00:00+0100',
    '2025-01-01T00:00:00+0000',
    '2025-12-30T23:30:00-05:00',
])
def test_dataset_updated_before_the_economic_period_end_is_refused(stamp):
    obj=inputs();obj['field_support']['EZ.annual_current_account']['dataset_updated_at']=stamp
    refused(obj)


@pytest.mark.parametrize('stamp',[
    '2025-12-31T23:00:00+0100',
    '2025-12-31T23:30:00-05:00',
    '2026-01-01T00:00:00+0100',
    '2026-01-01T00:00:00+0000',
    '2026-10-28T23:00:00+0100',
    '2026-10-28T23:00:00.123+0100',
])
def test_dataset_updated_on_or_after_the_period_end_is_accepted(stamp):
    obj=inputs();obj['field_support']['EZ.annual_current_account']['dataset_updated_at']=stamp
    out=field(obj)
    assert out['quality']=='qualified' and out['support']['dataset_updated_at']==stamp


@pytest.mark.parametrize('observation',[
    '2026-01-01',
    '2025-12-30',
    '2026-10-28',
    '2025-12-31T00:00:00+00:00',
    '2025-12-31T00:00:00+0000',
])
def test_observation_at_must_be_the_exact_period_end_date(observation):
    obj=inputs();obj['measures']['EZ.annual_current_account']['observation_at']=observation
    refused(obj)


@pytest.mark.parametrize('period',[
    None,
    {'start':'2024-01-01','end':'2025-01-01','count':1,'count_basis':'release_periods'},
    {'start':'2025-01-01','end':'2026-01-01','count':2,'count_basis':'release_periods'},
    {'start':'2025-01-01','end':'2026-01-01','count':1,'count_basis':'observations'},
])
def test_the_civil_period_must_match_the_field_year(period):
    obj=inputs();obj['measures']['EZ.annual_current_account']['period']=period
    refused(obj)


@pytest.mark.parametrize('year',[True,'2025',0,9999])
def test_field_year_must_be_a_plain_civil_year(year):
    obj=inputs();obj['field_support']['EZ.annual_current_account']['field_year']=year
    refused(obj)


@pytest.mark.parametrize('metadata',['denied','unknown'])
def test_denied_metadata_hides_the_statistical_cell(metadata):
    obj=inputs()
    obj['measures']['EZ.annual_current_account'].update(metadata=metadata,value=999,source_reference='SECRET')
    out=field(obj)
    assert set(out)=={'field','quality','reason'} and out['quality']!='qualified'
    assert 'SECRET' not in json.dumps(out) and '999' not in json.dumps(out)


def test_denied_value_permission_never_publishes_the_statistical_number():
    obj=inputs();obj['measures']['EZ.annual_current_account']['value_permission']='denied'
    out=field(obj)
    assert out['quality']=='denied' and out['reason']=='value_denied'
    assert out['value'] is None and 'support' not in out


@pytest.mark.parametrize('quality',['missing','failed','denied','unsupported','unknown'])
def test_non_qualified_qualities_never_carry_a_support_or_a_number(quality):
    obj=inputs();obj['measures']['EZ.annual_current_account']['quality']=quality
    out=field(obj)
    assert out['quality']==quality and out['value'] is None and 'support' not in out


def test_a_stale_statistical_cell_keeps_its_own_value_and_support():
    obj=inputs();obj['measures']['EZ.annual_current_account']['quality']='stale'
    out=field(obj)
    assert out['quality']=='stale' and out['value']==1.7 and out['reason']=='source_stale'
    assert out['support']['observation_type']=='statistical'


@pytest.mark.parametrize('kind',['actual','estimate','projection'])
def test_the_original_five_key_annual_branch_is_unchanged(kind):
    obj=inputs()
    obj['field_support']['EZ.annual_current_account']={'method_ref':'annual-owner','market_id':'EZ',
        'field_year':2025,'vintage':'2026-10-01','observation_type':kind}
    obj['measures']['EZ.annual_current_account']['observation_at']='2026-01-01'
    out=field(obj)
    assert out['quality']=='qualified' and out['value']==1.7
    assert set(out['support'])==_LEGACY_KEYS
    assert out['support']['observation_type']==kind
    assert out['support']['vintage']=='2026-10-01'


def test_the_original_branch_still_refuses_an_actual_before_the_period_end():
    obj=inputs()
    obj['field_support']['EZ.annual_current_account']={'method_ref':'annual-owner','market_id':'EZ',
        'field_year':2025,'vintage':'2026-10-01','observation_type':'actual'}
    obj['measures']['EZ.annual_current_account']['observation_at']='2025-12-31'
    refused(obj)
    obj['field_support']['EZ.annual_current_account']['observation_type']='projection'
    assert field(obj)['quality']=='qualified'


def test_the_original_branch_still_requires_a_non_null_vintage():
    obj=inputs()
    obj['field_support']['EZ.annual_current_account']={'method_ref':'annual-owner','market_id':'EZ',
        'field_year':2025,'vintage':None,'observation_type':'actual'}
    refused(obj)


def test_a_seven_key_support_cannot_smuggle_an_actual_classification():
    obj=inputs();obj['field_support']['EZ.annual_current_account']['observation_type']='actual'
    refused(obj)


def test_a_missing_support_entry_is_unavailable_not_a_crash():
    obj=inputs();del obj['field_support']['EZ.annual_current_account']
    refused(obj)


def test_the_statistical_support_is_detached_and_inputs_are_not_mutated():
    obj=inputs();before=deepcopy(obj)
    row=build_pressure_rows(**obj)[0]
    assert row['annual_current_account']['support'] is not obj['field_support']['EZ.annual_current_account']
    row['annual_current_account']['support']['field_year']=1999
    row['annual_current_account']['support']['dataset_updated_at']='mutated'
    assert obj==before


def test_the_statistical_variant_adds_no_composite_risk_judgement():
    row=build_pressure_rows(**inputs())[0]
    assert set(row)=={'market_id','name_en','name_zh','country_credit_change',
                      'constituent_breadth_50d','annual_current_account'}
