"""Causal meaning of actual owner standardized credit-change scores."""
from copy import deepcopy
import math
import pandas as pd
import pytest
from bs4 import BeautifulSoup
from engine.intl_risk import _leg
from tests.test_intl_workspace_integration import render_fixture


def velocity_owner(kind):
    decline=[10-i*.03 for i in range(100)]+[7.03-(i+1)*.001 for i in range(20)]
    values=decline if kind=='above' else [20-x for x in decline] if kind=='below' else [10+i*.1+math.sin(i*.25)*.4 for i in range(120)]
    s=pd.Series(values,index=pd.bdate_range('2026-01-01',periods=120))
    if kind=='near':s.iloc[-1]=s.iloc[-21]+s.iloc[:-1].diff(20).dropna().mean()
    raw=float(s.iloc[-1]-s.iloc[-21]);leg=_leg(s,252,'synthetic_credit')
    return leg,raw


def credit_velocity_fixture():
    above,_=velocity_owner('above');below,_=velocity_owner('below');near,_=velocity_owner('near')
    return {'em_stress':{'legs':{'em_hy_oas':above}},'two_tier':{'tier1':{'regional_oas':{'asia':below,'latam':near,'emea':None}}}}


@pytest.mark.parametrize('kind,expected',[('above','Above usual 20d change'),('below','Below usual 20d change'),('near','Near usual 20d change')])
def test_credit_score_is_not_raw_spread_direction(kind,expected):
    leg,raw=velocity_owner(kind)
    if kind=='above':assert raw<0 and leg['vel_20d_z']>0.1
    elif kind=='below':assert raw>0 and leg['vel_20d_z'] < -0.1
    else:assert raw>1 and abs(leg['vel_20d_z'])<=0.1
    payload={'em_stress':{'legs':{'em_hy_oas':leg}},'two_tier':{'tier1':{'regional_oas':{k:leg for k in ('asia','latam','emea')}}}}
    original=deepcopy(payload)
    soup=BeautifulSoup(render_fixture(risk_desk=payload),'html.parser')
    for card in soup.select('.ird-spread-card'):
        label=card.select_one('.sc-vel');text=label.get_text(' ',strip=True)
        assert expected in text
        assert not any(word in text for word in ('Widening','Tightening','Steady','↑','↓','→'))
        assert 'vel-up' not in label.get('class',[]) and 'vel-dn' not in label.get('class',[])
        assert card.select_one('.sc-val').get_text(strip=True)==f"{leg['value']:.2f}%"
    assert payload==original
