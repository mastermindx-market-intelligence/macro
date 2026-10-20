"""Risk summary coverage follows actual owner threshold inputs, never absence-as-calm."""
from copy import deepcopy
from functools import lru_cache
from unittest.mock import patch
import numpy as np
import pandas as pd
import pytest
from bs4 import BeautifulSoup
from engine.contagion import two_tier_read
from tests.test_intl_dollar_funding_render import _funding_owner
from tests.test_intl_workspace_integration import render_fixture


@lru_cache(maxsize=6)
def transmission_owner(kind):
    if kind in ('absent','partial','partial_hot'):
        return _funding_owner({'absent':'absent','partial':'not_triggered','partial_hot':'triggered'}[kind])
    n=6 if kind=='short_hy' else 400;idx=pd.bdate_range('2025-01-01',periods=n)
    hy=pd.Series(3+.02*np.sin(np.arange(n)),index=idx)
    spy=pd.Series(100+np.arange(n)/10,index=idx);kre=spy.copy()
    move=pd.Series(80.,index=idx);move.iloc[-1]=60.
    sofr=pd.Series(4.5,index=idx);iorb=sofr.copy()
    dxy=pd.Series(100+np.arange(n)/20,index=idx);dgs2=pd.Series(4-np.arange(n)/1000,index=idx)
    if kind=='complete_hot':
        hy.iloc[-1]+=2;kre.iloc[-1]*=.8;move.iloc[-1]=120.;sofr.iloc[-5:]+= .1
    def fred(key):
        if kind=='short_hy':return hy if key=='BAMLH0A0HYM2' else None
        return {'BAMLH0A0HYM2':hy,'SOFR':sofr,'IORB':iorb,'DGS2':dgs2}.get(key)
    def stored(provider,key):
        if kind=='short_hy':return None
        series={'_MOVE':move,'DX-Y.NYB':dxy}.get(key)
        return None if series is None else pd.DataFrame({'close':series})
    with patch('engine.contagion._fred_series',side_effect=fred), \
         patch('engine.contagion._load_etf_close',side_effect=lambda key:None if kind=='short_hy' else {'SPY':spy,'KRE':kre}.get(key)), \
         patch('engine.contagion.store.read',side_effect=stored):
        return two_tier_read(em_stress_state='unknown')


def transmission_fixture(kind='absent'):
    return {'two_tier':deepcopy(transmission_owner(kind))}


def rendered_transmission(payload):
    soup=BeautifulSoup(render_fixture(risk_desk=payload),'html.parser')
    return soup.select('.ird-hchip')[1],soup.select_one('#intl-contagion').find_parent('div',class_='panel')


@pytest.mark.parametrize('kind,assessed,hot',[('absent',0,0),('short_hy',0,0),('partial',1,0),('partial_hot',1,1),('complete_cold',4,0),('complete_hot',4,4)])
def test_actual_threshold_coverage_never_claims_five_measured_channels(kind,assessed,hot):
    payload=transmission_fixture(kind);before=deepcopy(payload)
    assert payload['two_tier']['tier2']['hot_count']==hot
    chip,panel=rendered_transmission(payload);text=chip.get_text(' ',strip=True)
    assert f'{assessed}/4 assessed' in text and f'{assessed}/4已评估' in text
    assert f'{hot} triggered' in text and f'{hot}项触发' in text
    if assessed==0:assert 'Unavailable' in chip.select_one('.hc-state').get_text()
    assert not any(word in text for word in ['Not reaching','Ignore for US book','Tighten stops','of 5','可忽略','收紧美股止损'])
    assert 'state-ok' not in chip.get('class',[])
    assert payload==before
    channels=panel.select_one('.ird-channels')
    assert len(channels.select('[data-transmission-leg]'))==4
    assert sum('Unavailable' not in node.get_text() for node in channels.select('[data-transmission-leg]'))==assessed


def test_safety_flag_stays_informational_and_outside_threshold_denominator():
    payload=transmission_fixture('complete_cold');chip,panel=rendered_transmission(payload)
    assert payload['two_tier']['safety_bid'] is True
    safety=panel.select_one('[data-transmission-safety]')
    assert safety is not None and 'Informational' in safety.get_text() and 'Flagged' in safety.get_text()
    assert '信息项' in safety.get_text() and '已标记' in safety.get_text()
    assert '0 triggered' in chip.get_text()


@pytest.mark.parametrize('flag',[None,'false',0])
def test_untyped_hot_flag_is_not_assessed(flag):
    payload=transmission_fixture('partial');payload['two_tier']['tier2']['legs']['sofr_iorb_corridor']['hot']=flag
    chip,_=rendered_transmission(payload)
    assert '0/4 assessed' in chip.get_text() and 'Unavailable' in chip.select_one('.hc-state').get_text()
