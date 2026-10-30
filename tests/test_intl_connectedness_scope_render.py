"""Descriptive connectedness follows owner variance shares, not causal speed."""
from contextlib import redirect_stdout
from copy import deepcopy
from functools import lru_cache
from io import StringIO
from unittest.mock import patch
import numpy as np
import pandas as pd
import pytest
from bs4 import BeautifulSoup
from engine.contagion import spillover, _dy_connectedness
from tests.test_intl_workspace_integration import render_fixture


@lru_cache(maxsize=3)
def connectedness_owner(kind='complete'):
    idx=pd.bdate_range('2025-01-01',periods=220);rng=np.random.default_rng(8724)
    shared=rng.normal(0,.006,len(idx));series={}
    for ticker in ['SPY','EWJ','EWG']:
        series[ticker]=pd.Series(100*np.exp(np.cumsum(shared+rng.normal(0,.005,len(idx)))),index=idx)
    with patch('engine.contagion._load_etf_ohlc',return_value=None), \
         patch('engine.contagion._load_etf_close',side_effect=lambda t:None if kind=='absent' else series.get(t)), \
         redirect_stdout(StringIO()):
        return spillover()


def connectedness_fixture(kind='complete'):
    owner=deepcopy(connectedness_owner('absent' if kind=='absent' else 'complete'))
    if kind in ('zero','matrix'):
        theta=np.eye(3) if kind=='zero' else np.array([[.8,.1,.1],[.8,.1,.1],[.8,.1,.1]])
        c=_dy_connectedness(theta);tickers=['SPY','EWJ','EWG']
        owner.update(total_connectedness=round(c['total'],1),us_from_others=round(c['from_others'][0]*100,1),
            top_transmitters=[{'ticker':t,'to_others_pct':round(c['to_others'][i]*100,1)} for i,t in enumerate(tickers)])
    if kind=='missing_params':owner.pop('params',None)
    if kind=='missing_date':owner['as_of']=None
    if kind=='escaped_date':owner['as_of']='<img src=x onerror=alert(1)>'
    tx=[dict(t,name_en=t['ticker'],name_zh=t['ticker'],flag='') for t in owner['top_transmitters']]
    return {'spillover':owner,'top_transmitters_display':tx}


def connectedness_panel(payload):
    soup=BeautifulSoup(render_fixture(risk_desk=payload),'html.parser')
    return soup.select_one('#intl-contagion').find_parent('div',class_='panel')


@pytest.mark.parametrize('kind',['absent','complete','zero','matrix'])
def test_model_values_never_become_speed_global_causal_shares_or_daily_return_inputs(kind):
    payload=connectedness_fixture(kind);before=deepcopy(payload);owner=payload['spillover']
    panel=connectedness_panel(payload);text=panel.get_text(' ',strip=True)
    assert 'Modelled volatility links' in text and '模型波动率关联' in text
    assert 'row-normalized' in text and '逐行归一化' in text
    assert 'not transmission speed' in text and '非传播速度' in text
    assert not any(phrase in text for phrase in ['shocks travel fast','spread faster','shocks spread','quickly reach','daily ETF returns','global shock variance is absorbed','压力可快速蔓延','ETF日度收益'])
    if kind=='absent':
        assert panel.select_one('.dc-num') is None and panel.select_one('.ur-num') is None
        assert 'Connectedness data not available' in text
    else:
        assert panel.select_one('.dc-num').get_text()==f"{owner['total_connectedness']:.0f}"
        assert panel.select_one('.ur-num').get_text()==f"{owner['us_from_others']:.1f}%"
        assert 'SPY volatility variance share' in text and 'SPY波动率方差份额' in text
        assert '150 aligned observations' in text and 'lag 2' in text and 'horizon 10 steps' in text
        series=panel.find(string=lambda text: text and text.strip()=='Model series:').parent.parent
        assert series.get_text(' ',strip=True).endswith('3') and '模型序列：' in series.get_text()
        assert 'Largest outbound model contributions' in text
        tip=panel.select_one('.ird-tx-row')['data-tip-en']
        assert 'summed percentage points' in tip and 'may exceed 100' in tip and 'points of stress' not in tip
        if kind=='matrix':assert '160.0' in tip
    assert payload==before


def test_absent_method_parameters_are_not_filled_with_default_windows():
    panel=connectedness_panel(connectedness_fixture('missing_params'))
    method=panel.select_one('[data-connectedness-method]').get_text(' ',strip=True)
    assert 'Unavailable' in method and '150' not in method and '10 steps' not in method


@pytest.mark.parametrize('kind',['absent','missing_date','escaped_date'])
def test_snapshot_clock_is_scoped_escaped_and_never_borrowed(kind):
    panel=connectedness_panel(connectedness_fixture(kind));clock=panel.select_one('[data-connectedness-clock]')
    assert clock is not None
    assert 'Model snapshot date:' in clock.get_text() and '模型快照日期：' in clock.get_text()
    if kind=='escaped_date':
        assert '<img src=x onerror=alert(1)>' in clock.get_text()
        assert clock.select_one('img') is None
    else:
        assert 'Unavailable' in clock.get_text() and '不可用' in clock.get_text() and 'n/a' not in clock.get_text()
