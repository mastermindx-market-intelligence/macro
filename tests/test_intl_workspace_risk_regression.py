import pytest
from tests.test_intl_workspace_risk import valid_call
from lib.intl_workspace_risk import qualify_us_transmission

def test_actual_owner_nested_safety_bid_does_not_suppress_qualified_state():
    raw,elig=valid_call()
    raw['tier2']['legs']['safety_bid_flag']={'safety_bid':True,'hot':False}
    out=qualify_us_transmission(two_tier=raw,eligibility=elig)
    assert out['quality']=='qualified' and out['state']=='contained'

def test_permitted_diagnostic_survives_unsupported_origin():
    raw,elig=valid_call('quiet')
    raw['tier1']['em_stress_state']='unknown'
    out=qualify_us_transmission(two_tier=raw,eligibility=elig)
    assert out['state'] is None and out['quality']=='unknown'
    assert out['diagnostic']=={'reported_state':'quiet'}

def test_hostile_class_property_is_not_accessed():
    class Hostile:
        @property
        def __class__(self):
            raise AssertionError('executed external property')
    out=qualify_us_transmission(two_tier=Hostile(),eligibility=None)
    assert out['state'] is None
