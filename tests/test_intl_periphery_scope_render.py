"""Periphery presentation respects owner absence, rounded precision and clock scope."""
from copy import deepcopy
from functools import lru_cache
from unittest.mock import patch
import pandas as pd
import pytest
from bs4 import BeautifulSoup
from engine import intl_compare
from tests.test_intl_rates_render import rates_render_fixture, no_data_io
from tests.test_intl_workspace_integration import render_fixture


@lru_cache(maxsize=6)
def _periphery_owner(kind):
    n,delta={'missing':(3,0),'flat':(70,0),'tiny_down':(70,-.001),
             'tiny_up':(70,.001),'down':(70,-.3),'up':(70,.3)}[kind]
    idx=pd.bdate_range('2026-01-01',periods=n)
    de=pd.Series(2.,index=idx);it=pd.Series(3.,index=idx);it.iloc[-1]+=delta
    with patch('engine.intl_inputs.read_intl_macro_col',side_effect=lambda key:{'de_10y':de,'it_10y':it}.get(key)):
        return intl_compare.periphery_panel()


def periphery_scope_fixture():
    rates=rates_render_fixture()
    rows=[]
    for i,kind in enumerate(['missing','flat','tiny_down','tiny_up','down','up']):
        row=deepcopy(_periphery_owner(kind)['spreads'][0])
        row.update(label=f'Synthetic case {i+1}',label_zh=f'合成案例{i+1}',flag='')
        rows.append(row)
    rates['periphery']={'asof':'2026-04-08','spreads':rows}
    return rates


def periphery_panel(rates):
    return BeautifulSoup(render_fixture(rates=rates),'html.parser').select_one('#intl-euro-fragmentation').parent


@pytest.mark.parametrize('kind,en,zh',[
    ('missing','Unavailable','不可用'),('flat','Non-widening at supplied precision','所供精度下未走阔'),
    ('tiny_down','Non-widening at supplied precision','所供精度下未走阔'),
    ('tiny_up','Widening','走阔'),('down','Tightening','收窄'),('up','Widening','走阔'),
])
def test_actual_periphery_read_preserves_absence_and_rounded_direction(kind,en,zh):
    rates=rates_render_fixture();rates['periphery']=deepcopy(_periphery_owner(kind));before=deepcopy(rates)
    row=periphery_panel(rates).select_one('tbody tr');read=row.select('td')[-1]
    assert en.lower() in read.get_text().lower() and zh in read.get_text()
    if kind in ['missing','flat','tiny_down']:
        assert 'tightening' not in read.get_text().lower() and '收窄' not in read.get_text()
        assert not read.select('.ok,.pos,.neg')
    if kind=='missing':
        assert row.select('td')[2].get('class',[])==[]
    assert rates==before


@pytest.mark.parametrize('date',[None,'2026-04-08','<script>bad()</script>'])
def test_periphery_clock_names_bund_scope_without_borrowing_row_clocks(date):
    rates=periphery_scope_fixture();rates['periphery']['asof']=date
    panel=periphery_panel(rates);clock=panel.select_one('[data-periphery-date]')
    assert clock is not None
    assert 'Bund series date:' in clock.get_text() and '德债序列日期：' in clock.get_text()
    assert (date or 'Unavailable') in clock.get_text()
    assert 'Individual spread observation dates unavailable' in clock.get_text()
    assert clock.find('script') is None


def test_periphery_method_describes_comparison_not_a_proven_stress_cause():
    panel=periphery_panel(periphery_scope_fixture());text=panel.get_text(' ',strip=True)
    assert '63 supplied intervals' in text and 'not a causal stress diagnosis' in text
    assert 'Wider spreads mean more Eurozone stress' not in text
    assert 'not distinguish an exact zero from a small negative change' in text


@pytest.mark.parametrize('flag',[None,'false',0])
def test_untyped_widening_flag_does_not_create_direction(flag):
    rates=periphery_scope_fixture();rates['periphery']['spreads']=[dict(rates['periphery']['spreads'][-1],widening=flag)]
    read=periphery_panel(rates).select_one('tbody tr').select('td')[-1]
    assert 'Unavailable' in read.get_text() and '不可用' in read.get_text()
