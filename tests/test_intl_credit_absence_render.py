"""Bounded Credit/bond absence cases; synthetic inputs through existing owners."""
from copy import deepcopy
from unittest.mock import patch
import pandas as pd
import pytest
from bs4 import BeautifulSoup
from engine.intl_bonds import inversion_board
from engine.intl_risk import _leg
from tests.test_intl_workspace_integration import render_fixture


def panel(payload):
    soup=BeautifulSoup(render_fixture(risk_desk=payload), 'html.parser')
    return soup.select_one('#intl-credit-bonds').find_parent('div',class_='panel')


def inversion_fixture(kind):
    values={'empty':{},'zero':{'US':(3.,2.),'DE':(2.,1.)},'mixed':{'US':(1.,2.),'DE':(2.,1.)},'all':{'US':(1.,2.),'DE':(1.,2.)},'flat':{'US':(0.,0.)}}[kind]
    def load(spec,leg):
        pair=values.get(spec['code'])
        if pair is None or leg=='short': return None
        return pd.Series([pair[0 if leg=='y10' else 1]],index=pd.to_datetime(['2026-10-14']))
    with patch('engine.intl_bonds._load_series_standalone',load):
        return inversion_board()


@pytest.mark.parametrize('kind',['absent','empty','one_observation','real_zero'])
def test_credit_missing_velocity_is_not_steady(kind):
    if kind=='one_observation':
        series=pd.Series([0.0],index=pd.to_datetime(['2026-10-14']))
        leg=_leg(series,252,'synthetic')
        assert leg['value']==0 and leg['vel_20d_z'] is None
    elif kind=='real_zero': leg={'value':0.0,'vel_20d_z':0.0}
    else: leg=None
    payload={'cb_desk':{}}
    if kind!='absent':
        payload.update(em_stress={'legs':{'em_hy_oas':leg}},two_tier={'tier1':{'regional_oas':{k:leg for k in ('asia','latam','emea')}}})
    original=deepcopy(payload)
    cards=panel(payload).select('.ird-spread-card')
    assert len(cards)==4
    for card in cards:
        velocity=card.select_one('.sc-vel').get_text(' ',strip=True)
        assert ('Near usual 20d change' if kind=='real_zero' else 'Unavailable') in velocity
        if kind!='real_zero': assert 'Steady' not in velocity and '→' not in velocity
        assert card.select_one('.sc-val').get_text(strip=True)==('0.00%' if kind in ('one_observation','real_zero') else '—')
    assert payload==original


@pytest.mark.parametrize('kind',['absent','empty','zero','mixed','all','flat'])
def test_inversion_missing_coverage_never_invents_six_positive_curves(kind):
    owner=None if kind=='absent' else inversion_fixture(kind)
    payload={'cb_desk':{}}
    if owner is not None: payload['inversion_board']=owner
    original=deepcopy(payload)
    row=panel(payload).select_one('.ird-inv-row')
    text=row.get_text(' ',strip=True)
    if kind in ('absent','empty'):
        assert 'Unavailable' in text
        assert '0 / 6' not in text and 'no recession signal' not in text and 'positively sloped' not in text
    else:
        assert row.select_one('.inv-num').get_text(strip=True)==f"{owner['n_inverted']} / {owner['n_total']}"
        if kind=='flat': assert 'positively sloped' not in text
    assert payload==original


def credit_absence_fixture():
    leg=_leg(pd.Series([0.0],index=pd.to_datetime(['2026-10-14'])),252,'synthetic')
    return {'em_stress':{'legs':{'em_hy_oas':leg}},'two_tier':{'tier1':{'regional_oas':{'asia':None,'latam':{'value':0.0,'vel_20d_z':0.0},'emea':{'value':1.25,'vel_20d_z':None}}}},'inversion_board':inversion_fixture('empty')}
