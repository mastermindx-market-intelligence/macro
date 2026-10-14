"""EM summary reports owner aggregation coverage, without absence-as-calm."""
from contextlib import ExitStack
from copy import deepcopy
from functools import lru_cache
from unittest.mock import patch
import pytest
from bs4 import BeautifulSoup
from engine.intl_risk import em_stress
from tests.test_intl_workspace_integration import render_fixture


@lru_cache(maxsize=8)
def em_owner(available=0, hot=0):
    names=['_leg_em_hy_oas','_leg_vxeem','_leg_em_fx_basket',
           '_leg_em_equity_breadth','_leg_em_dollar_vel','_leg_emb_ief']
    with ExitStack() as stack:
        for index,name in enumerate(names):
            leg=None if index>=available else {'value':1.,'pctile':90. if index<hot else 30.,
                'vel_20d_z':0.,'_adverse_direction':'up','asof':'2026-10-13'}
            stack.enter_context(patch('engine.intl_risk.'+name,return_value=leg))
        return em_stress()


def em_fixture(available=0, hot=0):
    return {'em_stress':deepcopy(em_owner(available,hot))}


def em_chip(payload):
    return BeautifulSoup(render_fixture(risk_desk=payload),'html.parser').select('.ird-hchip')[0]


@pytest.mark.parametrize('available,hot,state',[(0,0,'insufficient_data'),(1,0,'insufficient_data'),
    (2,2,'insufficient_data'),(3,0,'calm'),(6,0,'calm'),(3,2,'strained'),(6,3,'stressed')])
def test_actual_owner_state_keeps_coverage_and_never_instructs_positions(available,hot,state):
    payload=em_fixture(available,hot);before=deepcopy(payload)
    assert payload['em_stress']['state']==state
    chip=em_chip(payload);text=chip.get_text(' ',strip=True)
    assert f'{available}/6 signals available' in text and f'{available}/6项指标可用' in text
    assert f'{hot} triggered' in text and f'{hot}项触发' in text
    label={'calm':'Calm','strained':'Strained','stressed':'Stressed','insufficient_data':'Unavailable'}[state]
    assert label in chip.select_one('.hc-state').get_text()
    assert 'Indicator state' in text and '指标状态' in text
    assert 'Coincident indicator' in text and '同步指标' in text
    assert not any(word in text for word in ['All stress','No action','Watch','EM positions','所有压力','无需操作','仓位','明日再查'])
    assert 'state-ok' not in chip.get('class',[])
    assert payload==before


@pytest.mark.parametrize('field,value',[('n_legs_available',None),('n_legs_available',False),
    ('n_legs_total',None),('legs_hot',None)])
def test_missing_or_untyped_coverage_does_not_become_zero_or_six(field,value):
    payload=em_fixture(6,0);payload['em_stress'][field]=value
    chip=em_chip(payload);text=chip.get_text(' ',strip=True)
    assert 'Unavailable' in chip.select_one('.hc-state').get_text()
    assert 'Coverage unavailable' in text and '覆盖数据不可用' in text
    assert '0 triggered' not in text and '6/6' not in text
