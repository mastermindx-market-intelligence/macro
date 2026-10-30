"""ECB balance-sheet read preserves supplied precision and weekly-bin clock."""
from copy import deepcopy
from functools import lru_cache
from unittest.mock import patch
import re
import pandas as pd
import pytest
from bs4 import BeautifulSoup
from engine import intl_rates
from tests.test_intl_rates_render import rates_render_fixture, no_data_io
from tests.test_intl_workspace_integration import render_fixture


@lru_cache(maxsize=5)
def ecb_owner(kind):
    delta={'flat':0.,'up':.1,'down':-.1,'tiny_up':.00001,'tiny_down':-.00001}[kind]
    idx=pd.date_range('2025-01-06',periods=65,freq='W-MON')
    series=pd.Series(6e6,index=idx);series.iloc[-1]*=1+delta
    with patch('engine.intl_rates._series',return_value=series):
        return intl_rates.ecb_liquidity_impulse()


def ecb_scope_fixture(kind='flat'):
    rates=rates_render_fixture();rates['liquidity']=deepcopy(ecb_owner(kind))
    return rates


def ecb_card(rates):
    soup=BeautifulSoup(render_fixture(rates=rates),'html.parser')
    # Existing card's unique bilingual heading; no fabricated panel route.
    return next(n for n in soup.select('.rcard') if 'ECB balance-sheet impulse' in n.get_text())


@pytest.mark.parametrize('kind,en,zh',[
    ('flat','Non-decreasing at supplied precision','所供精度下未下降'),
    ('tiny_up','Non-decreasing at supplied precision','所供精度下未下降'),
    ('tiny_down','Lower than 52 weeks ago','低于52周前'),
    ('up','Higher than 52 weeks ago','高于52周前'),
    ('down','Lower than 52 weeks ago','低于52周前'),
])
def test_ecb_owner_change_is_not_a_policy_easing_verdict(kind,en,zh):
    rates=ecb_scope_fixture(kind);before=deepcopy(rates);card=ecb_card(rates)
    assert en in card.select_one('.rh').get_text() and zh in card.select_one('.rh').get_text()
    assert not re.search(r'\beasing\b', card.get_text().lower()) and 'QT' not in card.get_text()
    assert not card.select('.shape.normal,.shape.inverted,.rgrid .pos,.rgrid .neg')
    assert rates==before


@pytest.mark.parametrize('clock',[None,'2026-04-05','<script>bad()</script>'])
def test_ecb_weekly_bin_is_not_an_observation_date(clock):
    rates=ecb_scope_fixture();rates['liquidity']['asof']=clock
    card=ecb_card(rates);text=card.get_text(' ',strip=True)
    assert 'Weekly bin ending' in text and '周分箱结束日' in text
    assert (clock or 'Unavailable') in text
    assert 'Observation date unavailable' in text and '观测日期不可用' in text
    assert card.find('script') is None


def test_ecb_method_discloses_resampling_and_forward_fill():
    text=ecb_card(ecb_scope_fixture()).get_text(' ',strip=True)
    assert 'last observation in each weekly bin' in text and 'forward-filled' in text
    assert 'not a policy-action classification' in text
    assert 'not distinguish exact zero from a small positive change' in text


@pytest.mark.parametrize('flag',[None,'false',0])
def test_ecb_untyped_draining_flag_does_not_invent_a_direction(flag):
    rates=ecb_scope_fixture();rates['liquidity']['draining']=flag
    heading=ecb_card(rates).select_one('.rh').get_text()
    assert 'Unavailable' in heading and '不可用' in heading
